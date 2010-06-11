#!/usr/bin/env python
from request import HttpRequest, REDIRECT_INFINITE, REDIRECT_REFUSE
from response import HttpResponse
from errors import *
from client import HttpClient, PROGRESS_CALLBACK_CONTINUE, PROGRESS_CALLBACK_ABORT 
from dnscache import DnsCache
from flowcontrol import SiteProfile
from connpool import BaseConnection, ConnectionPool

__all__ = ['HttpRequest', 'REDIRECT_INFINITE', 'REDIRECT_REFUSE',
           'HttpResponse', 'HttpClient', 
           'PROGRESS_CALLBACK_CONTINUE', 'PROGRESS_CALLBACK_ABORT',
           'DnsCache', 'SiteProfile',
           'UnsupportedProtocol', 'TooManyRedirects', 'ConnectError',
           'ProxyResolveError', 'HostResolveError', 'OperationTimeoutError',
           'BaseConnection', 'ConnectionPool',
           'Request', 'urlopen',]

Request = HttpRequest

def urlopen(url_or_request, data_or_reader=None, 
            guess_encoding=None, progress_callback=None,
            session_timeout=None, connect_timeout=None,
            *args, **kwds):
    
    if issubclass(type(url_or_request), HttpRequest):
        request = url_or_request
    else:
        request = HttpRequest(str(url_or_request), data_or_reader, **kwds)
        
    if session_timeout or connect_timeout:
        profile = SiteProfile.get(request.hostname)
        profile.timeout = session_timeout
        profile.connect_timeout = connect_timeout
    else:
        profile = None
        
    return HttpClient(profile=profile, guess_encoding=guess_encoding).perform(request, progress_callback)