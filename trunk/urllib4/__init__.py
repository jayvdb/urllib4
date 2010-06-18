#!/usr/bin/env python
import os
from tempfile import mkstemp

from request import HttpRequest, REDIRECT_INFINITE, REDIRECT_REFUSE
from response import HttpResponse
from errors import *
from client import HttpClient, PROGRESS_CALLBACK_CONTINUE, PROGRESS_CALLBACK_ABORT
from dnscache import DnsCache
from pagecache import DictPageCache, MemcachePageCache
from flowcontrol import SiteProfile
from connpool import BaseConnection, ConnectionPool

__all__ = ['HttpRequest', 'REDIRECT_INFINITE', 'REDIRECT_REFUSE',
           'HttpResponse', 'HttpClient',
           'PROGRESS_CALLBACK_CONTINUE', 'PROGRESS_CALLBACK_ABORT',
           'DnsCache', 'DictPageCache', 'MemcachePageCache', 'SiteProfile',
           'UnsupportedProtocol', 'TooManyRedirects', 'ConnectError',
           'ProxyResolveError', 'HostResolveError', 'OperationTimeoutError',
           'BaseConnection', 'ConnectionPool',
           'Request', 'urlopen',]

Request = HttpRequest

def urlopen(url_or_request, data_or_reader=None, headers={}, method=None,
            guess_encoding=None, dnscache=None, pagecache=None, progress_callback=None,
            session_timeout=None, connect_timeout=None, *args, **kwds):

    if issubclass(type(url_or_request), HttpRequest):
        request = url_or_request
    else:
        request = HttpRequest(str(url_or_request), data_or_reader, headers, method, **kwds)

    if session_timeout or connect_timeout:
        profile = SiteProfile.get(request.hostname)
        profile.timeout = session_timeout
        profile.connect_timeout = connect_timeout
    else:
        profile = None

    return HttpClient(dnscache=dnscache, pagecache=pagecache,
        profile=profile, guess_encoding=guess_encoding).perform(request, progress_callback)

def urlretrieve(url, filename=None, reporthook=None, data_or_reader=None,
                dnscache=None, pagecache=None, *args, **kwds):
    
    request = HttpRequest(url, data_or_reader, **kwds)
    client = HttpClient(dnscache=dnscache, pagecache=pagecache)

    if filename:
        client.file = open(filename)
    else:
        fd, filename = mkstemp()
        client.file = os.fdopen(fd)

    def progress(download_total, downloaded, upload_total, uploaded):
        reporthook(downloaded, 1, download_total)

    response = client.perform(request, progress if reporthook else None)

    return (filename, response.headers)
