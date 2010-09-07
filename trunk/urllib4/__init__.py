#!/usr/bin/env python
import os
from tempfile import mkstemp

from request import HttpRequest, REDIRECT_INFINITE, REDIRECT_REFUSE
from response import HttpResponse
from errors import *
from client import HttpClient, PROGRESS_CALLBACK_CONTINUE, PROGRESS_CALLBACK_ABORT
from pipeline import HttpPipeline
from dnscache import DnsCache
from pagecache import DictPageCache, MemcachePageCache
from flowcontrol import SiteProfile
from connpool import BaseConnection, ConnectionPool
from adapter import Request, urlopen, urlretrieve

__version__ = '0.3'
__author__ = 'Flier Lu <flier.lu@gmail.com>'
__url__ = 'http://code.google.com/p/urllib4/'
__all__ = ['HttpRequest', 'REDIRECT_INFINITE', 'REDIRECT_REFUSE',
           'HttpResponse', 'HttpClient', 'HttpPipeline',
           'PROGRESS_CALLBACK_CONTINUE', 'PROGRESS_CALLBACK_ABORT',
           'DnsCache', 'DictPageCache', 'MemcachePageCache', 'SiteProfile',
           'UnsupportedProtocol', 'TooManyRedirects', 'ConnectError',
           'ProxyResolveError', 'HostResolveError', 'OperationTimeoutError',
           'BaseConnection', 'ConnectionPool',
           'Request', 'urlopen',]
