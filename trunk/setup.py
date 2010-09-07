#!/usr/bin/env python
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = 'urllib4',
    version = '0.4',
    packages = find_packages(exclude=['ez_setup', 'tests']),
    author = 'Flier Lu',
    author_email = 'flier.lu@gmail.com',
    description = 'urllib style HTTP/FTP client library base on pycurl',
    long_description = open('README.txt').read(),
    license = 'Apache License 2.0',
    keywords = 'urllib pycurl network http ftp',
    url = 'http://code.google.com/p/urllib4/',
    download_url = 'http://code.google.com/p/urllib4/downloads/list',
    install_requires = [
        'pycurl >= 7.19',
        'BeautifulSoup >= 3.0.8',
        'python-memcached >= 1.45',
    ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development',
    ]
)
