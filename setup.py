"""Python PyPi packaging."""

from os.path import abspath, dirname, join
from setuptools import setup

setup(

    # Basic package information:
    name = 'stormpath-tenant-usage',
    version = '0.0.1',
    scripts = ('stormpath-tenant-usage.py',),

    # Packaging options:
    zip_safe = False,
    include_package_data = True,

    # Package dependencies:
    install_requires = [
        'psycopg2>=2.6.2', 'mandrill>=1.0.57', 'docopt==0.4.0',
        'twilio>=6.0', 'python-dateutil>=2.6.0', 'boto3>=1.4.4'
    ],

    # Metadata:
    author = 'Michele Degges',
    author_email = 'michele@stormpath.com',
    license = 'UNLICENSED',
    url = 'https://github.com/mdeggies/stormpath-tenant-usage',
    description = 'Queries redshift for a Stormpath tenants billed API usage information for X number of billing periods'

)
