stormpath-tenant-usage
================

Easily query Redshift to get a tenant's API usage information.

Installation
------------

Installing ``stormpath-tenant-usage`` is simple -- just use [pip][PIP]!

Once you have pip installed on your computer, you can run the following to\s\s
install the latest release of ``stormpath-tenant-usage``:

    $ pip install -U git+https://github.com/mdeggies/stormpath-tenant-usage.git.

Usage
-----

Before you can start, you'll need to configure ``stormpath-tenant-usage`` and give it your Stormpath Redshift credentials. To do this, simply run:

    $ stormpath-tenant-usage configure

This will store your credentials in the local file ``~/.redshift``. You'll never need to use Passpack or LastPass to store your Redshift credentials again!!

```
NOTE: DON'T FORGET! You need to define your environment variables. You'll need to create a Mandrill Account, a Twilio Account, and an AWS account. In future iterations of this project, we will all use the same accounts and protect these resources via an API.
```

To get the logs for a particular tenant, you'll just need to provide the tenant-name, and the number of billing periods you'd like to see -- this defaults to 1:

    $ stormpath-tenant-usage -t tenant-name -b 3

You can also specify your email address and SMS number -- doing so will encrypt the logs, store them in S3 and generate a link, and email them out. It will also send the decryption key via SMS:

    $ stormpath-tenant-usage -t tenant-name -b 3 -e something@mailinator.com -s +18188888888

This will query Redshift for all of the billed API usage logs for the tenant during their current billing period, and write this data to a CSV in a new directory named ``/stormpath-tenant-usage``. If you'd like to specify your own location,
you can do so by adding a location, like so:

    $ stormpath-tenant-usage -t tenant-name -l ~/super-secret-location -b 3

If you want to get a smaller set of logs that contain less than a months worth of data, you can do that, too!

    $ stormpath-tenant-usage -t tenant-name -S '2017-02-01 00:00:00' -E '2017-02-02 00:00:00'

You should see output similar to the following:

```
=== Connecting to Redshift ===
- Running query 1 for data in range 2017-05-05 00:00:00 to 2017-05-10 00:00:00...
- Writing data to file...
- Encrypting data with a secure, random key...
updating: tenant-name/ (stored 0%)
updating: tenant-name/1-tenant-name.csv (deflated 42%)
- Uploading file to S3...
Calling s3:list_buckets with {}
  Starting new HTTPS connection (1): s3.amazonaws.com
  Calling s3:put_object with {'Bucket': 'bucket-name', 'Key': 'tenant-name.zip', 'Body': <_io.BufferedReader name='/tenant-name.zip'>, 'ContentType': 'application/zip'}
  Starting new HTTPS connection (1): stormpath-tenant-usage.s3.amazonaws.com
  - Sending email to email-address@domain.com...
  - Sending decryption key via SMS...
```

```
NOTE: Depending on how many API calls have been made from the tenant, this can take awhile!
```

Once the process is finished, you can navigate the CSV file in the ``~/stormpath-tenant-usage``
directory. If you've specified an email address and SMS number, the encrypted logs will be uploaded to S3,
a link will be emailed out, and the decryption key will be sent via SMS.

For full usage information, run ``stormpath-tenant-usage -h``:

```
$ stormpath-tenant-usage
~~~~~~~~~~~~~~~~
Query redshift for a Stormpath tenant's billed API usage logs

Usage:
  stormpath-tenant-usage configure
  stormpath-tenant-usage (-t <tenant-name>)
  [-l <location>]
  [(-b <billing-periods>) | (-S <start-timestamp> -E <end-timestamp>)]
  [-e <email> -s <sms>]
  [-V]

Options:
  -h --help                               Show this screen.
  -v --version                            Show version.
  -t --tenant-name <tenant-name>          (Required) Name of the Stormpath tenant.
  -l --location <location>                Local directory to save the logs to [default: ~/stormpath-tenant-usage].
  -b --billing-periods <billing-periods>  Number of billing periods to query [default: 1].
  -S --start-timestamp <start-timestamp>  UTC start time (e.g. 2015-12-01 05:30:00).
  -E --end-timestamp <end-timestamp>      UTC end time   (e.g. 2016-01-01 05:30:00).
  -e --email <email>                      Email address that will receive the logs.
  -s --sms <sms>                          SMS number that will receive the decryption key needed to open the logs.
  -V --verbose                            Query for the raw, unaggregated logs? [default: False].


Written by Michele Degges.
```

Contribute
----------

Want to contribute? It's easy!

1. Fork this repo
2. Clone your fork, and create and checkout a new branch
3. Install the tool locally with ``pip install -e .``
4. Develop and test against the local tool
5. Push your branch to Github
6. Open a new pull request!

Help
----

Need help? Can't figure something out? If you think you've found a bug, please
open an issue on the [Github issue tracker][GIT].

Otherwise, [shoot me an email][SME]!

Changelog
---------

**0.0.2**: 2017-05-11

- Fixed docopt syntax and added a verbose logging option.

**0.0.1**: 2017-04-11

- First release! :)

[PIP]: http://pip.readthedocs.org/en/stable/ "pip"
[GIT]: https://github.com/mdeggies/stormpath-tenant-usage/issues "Github issue tracker"
[SME]: mailto:mdeggies@gmail.com?subject=HELP! "shoot me an email"
