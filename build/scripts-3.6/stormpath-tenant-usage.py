#!/Users/mdegges/.pyenv/versions/3.6.0/bin/python

"""
stormpath-tenant-usage
~~~~~~~~~~~~~~~~
Query redshift for a Stormpath tenant's billed API usage logs

Usage:
  stormpath-tenant-usage configure
  stormpath-tenant-usage (-t <tenant-name>)
    [-l <location>]
    [(-b <billing-periods>) | (-y <start-timestamp> -z <end-timestamp>)]
    [-e <email> -s <sms>]
    [-v]

Options:
    -t --tenant-name <tenant-name>          (Required) Name of the Stormpath tenant
    -l --location <location>                Local directory to save the logs to [default: ~/stormpath-tenant-usage]
    -b --billing-periods <billing-periods>  Number of billing periods to query [default: 1]
    -y --start-timestamp <start-timestamp>  UTC start time (e.g. 2015-12-01 05:30:00)
    -z --end-timestamp <end-timestamp>      UTC end time   (e.g. 2016-01-01 05:30:00)
    -e --email <email>                      Email address that will receive the logs
    -s --sms <sms>                          SMS number that will receive the decryption key needed to open the logs
    -v --verbose                            Query for the raw, unaggregated logs? [default: False]


Written by Michele Degges.
"""

from docopt import docopt
from builtins import input
from json import loads, dumps
from os import path, chmod, getcwd, makedirs, chdir, environ
from os.path import dirname, exists, expanduser
from mandrill import Mandrill
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from csv import writer
from psycopg2 import connect
from datetime import datetime
from dateutil import relativedelta
from subprocess import call
from string import ascii_letters, digits
from boto3 import resource
from sys import exit
import random, logging

CONFIG_FILE = expanduser('~/.redshift')
VERSION = 'stormpath-tenant-usage 0.0.2'
FILE_EXPIRATION_TIME = 86400

class ExportUsage(object):
    """Our CLI manager."""

    def __init__(self, tenant_name, location, billing_periods, verbose):
        """Open a Redshift connection and set global vars"""

        if exists(CONFIG_FILE):
            credentials = loads(open(CONFIG_FILE, 'r').read())
            self.setup_logger()
            logging.info('=== Connecting to Redshift ===')
            self.conn = connect(database=credentials.get('database'), port=credentials.get('port'), host=credentials.get('host'), user=credentials.get('username'), password=credentials.get('password'))
            self.cur = self.conn.cursor()
            self.tenant_name = tenant_name
            self.verbose = verbose
            self.location = self.set_location(location)
            self.billing_periods = self.set_billing_periods(billing_periods)
        else:
            logging.error('*** No Redshift credentials found! Please run stormpath-tenant-usage configure to set them up.')
            exit(1)

    def setup_logger(self):
        """
        Set up the logger to display all info/errors
        """

        logging.getLogger().setLevel(logging.INFO)
        logging.basicConfig(format='%(message)s')

    def get_timestamps(self):
        """
        Find all of the start and end timestamps for the requested billing periods.
        The timestamps object will be in this format:
        {
            3: { 'start': '2017-01-19 18:09:47', 'end': '2017-02-19 18:09:47' },
            2: { 'start': '2017-02-19 18:09:47', 'end': '2017-03-19 18:09:47' },
            1: { 'start': '2017-03-19 18:09:47', 'end': '2017-04-19 18:09:47' }
        }
        """

        # Get the current billing period timestamps.
        timestamp_query = """
            SELECT billing_period_start, billing_period_end FROM subscriptions
            JOIN requests ON subscriptions.tenant_uid = requests.tenant_uid
            WHERE tenant_name = %s LIMIT 1;
        """

        logging.info('- Retrieving billing periods...')
        self.cur.execute(timestamp_query, (self.tenant_name,))
        timestamp = self.cur.fetchone()

        if timestamp is None:
            logger.error('Data for this tenant is not available in Redshift.')
            exit(1)

        start = timestamp[0] # Current billing period start
        end = timestamp[1] # Current billing period end

        # Get the timestamps for all of the queries we need to run
        # and store them in an object
        timestamps = {}
        num = self.billing_periods

        while (num > 0):
            if num == 1:
                timestamps[num] = {
                    "start": start.strftime('%Y-%m-%d %H:%M:%S'),
                    "end": end.strftime('%Y-%m-%d %H:%M:%S')
                }
            elif num == 2:
                timestamps[num] = {
                    "start": (start + relativedelta.relativedelta(months=-1)).strftime('%Y-%m-%d %H:%M:%S'),
                    "end": (start).strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                months = -abs(num-1)
                timestamps[num] = {
                    "start": (start + relativedelta.relativedelta(months=months)).strftime('%Y-%m-%d %H:%M:%S'),
                    "end": (start + relativedelta.relativedelta(months=months+1)).strftime('%Y-%m-%d %H:%M:%S')
                }
            num=num-1

        self.query_redshift(timestamps)

    def query_redshift(self, timestamps):
        """
        Execute queries to get the billed API logs during the requested billing periods.
        CSV's will be named in this format:
            1-tenant-name.csv = current billing period logs
            2-tenant-name.csv = previous billing period logs
            3-tenant-name.csv = previous-previous billing period logs...
        """

        if self.verbose:
            billing_query = """
                SELECT uri, method, status, ip, requester_api_key_id, timestamp
                FROM requests JOIN subscriptions ON requests.tenant_uid = subscriptions.tenant_uid
                WHERE tenant_name = %s
                AND timestamp >= %s AND timestamp < %s
                AND billed='t';
            """
        else:
            billing_query = """
                SELECT count(1) AS apicount, uri, method, status, ip, requester_api_key_id,
                min(timestamp), max(timestamp)
                FROM requests JOIN subscriptions ON requests.tenant_uid = subscriptions.tenant_uid
                WHERE tenant_name = %s
                AND timestamp >= %s AND timestamp < %s
                AND billed='t' GROUP BY uri, method, status, ip, requester_api_key_id
                ORDER BY apicount DESC;
            """

        for i, timerange in timestamps.items():
            logging.info('- Running query {} for data in range {} to {}...'.format(i, timerange['start'], timerange['end']))
            self.cur.execute(billing_query, (self.tenant_name, timerange['start'], timerange['end']))
            csv_file = path.join(self.location, '%d-%s.csv' % (i, self.tenant_name))
            self.export_to_csv(csv_file)

    def send_sms(self, sms_number, encryption_key):
        """
        Send the decryption key via SMS to the mobile number provided.
        """

        twilio_client = Client(environ.get('TWILIO_ACCOUNT_SID'), environ.get('TWILIO_AUTH_TOKEN'))

        logging.info('- Sending decryption key via SMS: {}'.format(encryption_key))
        msg = twilio_client.messages.create(
            to=sms_number,
            from_="+16502810864",
            body="Decryption Key: {}".format(encryption_key),
        )

    def store_in_s3(self):
        """
        Connect to S3 bucket, and upload the encrypted zip file as an S3 object.
        """

        zip_file = '{}.zip'.format(self.tenant_name)

        s3 = resource(
            's3',
            aws_access_key_id=environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=environ.get('AWS_SECRET_ACCESS_KEY')
        )

        if (s3.Bucket(environ.get('S3_BUCKET')) not in s3.buckets.all()):
            bucket = s3.create_bucket(Bucket=environ.get('S3_BUCKET'))
        else:
            bucket = s3.Bucket(environ.get('S3_BUCKET'))

        file_path = getcwd() + '/' + zip_file
        s3.Object(environ.get('S3_BUCKET'), zip_file).put(Body=open(file_path, 'rb'), ContentType='application/zip')

        s3_client = s3.meta.client

        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': environ.get('S3_BUCKET'),
                'Key': zip_file
            }, ExpiresIn=FILE_EXPIRATION_TIME)

        return url

    def send_email(self, email_address, sms_number):
        """
        Send an email with a link to the encrypted zip file in S3.
        The link is a presigned url which gives the user access to
        download the file. Clicking on the link will download the file.
        """

        mandrill_client = Mandrill(environ.get('MANDRILL_API_KEY'))

        chdir(self.location)
        chdir('..')

        logging.info('- Encrypting data with a secure, random key...')
        encryption_key = ''.join(random.SystemRandom().choice(ascii_letters + digits) for _ in range(12))
        rc = call(['zip', '-P', encryption_key, '-r', self.tenant_name+'.zip', self.tenant_name+'/'])

        logging.info('- Uploading file to S3...')
        presigned_url = self.store_in_s3()
        s3_link = "<a href='{}'>{}</a>".format(presigned_url, 'USAGE LOGS (ZIP FILE DOWNLOAD)')

        logging.info('- Sending email to {}...'.format(email_address))

        message = {
            'from_email': 'support@stormpath.com',
            'from_name': 'Stormapth Support',
            'important': True,
            'to': [{'email': email_address,'type': 'to'}],
            'html': "<font size='4'><p>Hello from Stormpath Support!</p></font><font size='3'>\
            <p>The following link contains an encrypted ZIP file with your API usage logs for \
            tenant {}: {}. After downloading the attachment, unzip the file and extract the lo\
            gs using the passphrase that has been sent via SMS.</p><p>If you have any question\
            s about this process or the logs that have been sent to you, please feel free to r\
            eply to this email or <a href='https://support.stormpath.com/hc/en-us/requests/new\
            '>open a new Support Ticket</a>.</p><p>We will get back to you as soon as we can!<\
            /p><p>Cheers,</p><p>Stormpath Support</p></font>".format(self.tenant_name,s3_link)
        }

        try:
            result = mandrill_client.messages.send(message=message, async=False, ip_pool='Main Pool')

        except mandrill.Error as e:
            logging.error('A mandrill error occured: %s - %s'.format(e.__class__,e))

        self.send_sms(sms_number, encryption_key)

    def export_to_csv(self, csv_file):
        """Write Redshift queried usage data to a CSV."""

        if self.verbose:
            column_headers = ('URL', 'Method', 'Status', 'IP Address', 'Requester API Key ID', 'Timestamp (UTC)')
        else:
            column_headers = ('URL', 'Method', 'Status', 'IP Address', 'Requester API Key ID', 'Min Timestamp (UTC)', 'Max Timestamp (UTC)')

        with open(csv_file, 'w') as f:
            logging.info('- Writing data to file...')
            csv_writer = writer(f, delimiter='|')
            csv_writer.writerow(column_headers)
            csv_writer.writerows(self.cur)
            f.close()

    def set_billing_periods(self, billing_periods=None):
        """
        Return the number of billing periods to query.
        (The default is 1)
        """

        if not billing_periods:
            billing_periods = 1

        return int(billing_periods)

    def set_location(self, location=None):
        """
        Return the proper location to store the CSV (must be a directory).
        """

        if location == '~/stormpath-tenant-usage':
            location = expanduser("~") + '/stormpath-tenant-usage/'
            if not path.exists(location):
                makedirs(location)
            if not path.exists(location+self.tenant_name):
                chdir(location)
                makedirs(self.tenant_name)
        else:
            if not path.exists(location):
                makedirs(location)
            if not path.exists(location+self.tenant_name):
                chdir(location)
                makedirs(self.tenant_name)

        location += '/{}'.format(self.tenant_name)
        return location

def configure():
    """
    Initialize stormpath-tenant-usage.
    This will store Stormpath Redshift credentials in ~/.redshift,
    and ensure the credentials specified are valid.
    """

    logging.info('- Initializing `stormpath-tenant-usage`')
    logging.info('- To get started, we\'ll need to get your Stormpath Redshift credentials.')

    finished = False

    while not finished:
        database = input('- Enter your Redshift Database: ').strip()
        host = input('- Enter your Redshift Host: ').strip()
        port = input('- Enter your Redshift Port: ').strip()
        username = input('- Enter your Redshift Username: ').strip()
        password = input('- Enter your Redshift Password: ').strip()

        if not (database or host or port or username or password):
            logging.warn('- Provide your info, please...')
            continue

        try:
            # Validate the Redshift credentails.
            conn = connect(database=database, port=port, host=host, user=username, password=password)
            logging.info('- Successfully initialized ~/.redshift!')
            logging.info('- Your Redshift credentials are stored in the file: {}'.format(CONFIG_FILE))

            with open(CONFIG_FILE, 'w') as redshiftfg:
                redshiftfg.write(dumps({
                    "database": database,
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,
                }, indent=2))

            # Make the redshift configuration file only accessible to the current user
            chmod(CONFIG_FILE, 0o600)
            finished = True

        except Exception as e:
            logging.error('=== Your Redshift credentials are not working:\n{}'.format(e))

def main():
    """Handle user input, and do stuff accordingly."""

    arguments = docopt(__doc__, version=VERSION)

    # Configure Redshift credentials
    if arguments['configure']:
        configure()
        return

    print(arguments)

    exporter = ExportUsage(arguments['--tenant-name'], arguments['--location'], arguments['--billing-periods'], arguments['--verbose'])

    # Get one-off usage logs for a given start and end date/time
    if arguments['--start-timestamp'] is not None and arguments['--end-timestamp'] is not None:
        timestamps = {
            1: {
                "start": datetime.strptime(arguments['--start-timestamp'], '%Y-%m-%d %H:%M:%S'),
                "end": datetime.strptime(arguments['--end-timestamp'], '%Y-%m-%d %H:%M:%S')
            }
        }
        exporter.query_redshift(timestamps)
    # Get usage logs for X billing periods
    else:
        exporter.get_timestamps()

    # Send a link to the encrypted usage logs via email, and the decryption key via SMS
    if arguments['--email'] is not None and arguments['--sms'] is not None:
        exporter.send_email(arguments['--email'], arguments['--sms'])

if __name__ == '__main__':
    main()
