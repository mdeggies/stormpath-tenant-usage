stormpath-tenant-usage
================

Easily query Redshift to get a tenant's API usage information.

Installation
------------

Installing ``stormpath-tenant-usage`` is simple -- just use `pip`_!

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

    $ stormpath-tenant-usage -t tenant-name -st '2017-02-01 00:00:00' -et '2017-02-02 00:00:00'

You should see output similar to the following:

```
  === Connecting to Redshift ===
  - Retrieving billing periods...
  - Running query 1 for data in range START_TIME to END_TIME...
  - Writing to the file...
  - Encrypting file with a secure, random key...
  - Uploading file to S3...
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
    $ stormpath-tenant-usage -h

    stormpath-tenant-usage
    ~~~~~~~~~~~~~~~~
    Query redshift for a Stormpath tenant's billed API usage logs

    Usage:
      stormpath-tenant-usage configure
      stormpath-tenant-usage (-t <tenant-name> | --tenant-name <tenant-name>)
        [-l <location> | --location <location>]
        [-b <billing-periods> | --billing-periods <billing-periods>]
        [(-e <email> -s <sms>) | (--email <email> --sms <sms>)]
      stormpath-tenant-usage (-t <tenant-name> | --tenant-name <tenant-name>)
        [-l <location> | --location <location>]
        [(-st <start-timestamp> -et <end-timestamp>) | (--start <start-timestamp> --end <end-timestamp>)]
        [(-e <email> -s <sms>) | (--email <email> --sms <sms>)]

    Options:
      -h --help             Show this screen.
      -v --version          Show version.

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
open an issue on the `Github issue tracker`_.

Otherwise, `shoot me an email`_.

Changelog
---------

**0.0.1**: 2017-04-11

- First release! :)

.. _pip: http://pip.readthedocs.org/en/stable/ "pip"
.. _Github issue tracker: https://github.com/mdeggies/stormpath-tenant-usage/issues "stormpath-tenant-usage Issue Tracker"
.. _shoot me an email: mailto:michele@stormpath.com "HELP ME, MICHELE!"
