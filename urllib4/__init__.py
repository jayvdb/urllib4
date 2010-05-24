#!/usr/bin/env python
from request import HttpRequest, REDIRECT_INFINITE, REDIRECT_REFUSE
from response import HttpResponse
from errors import *
from client import HttpClient
from fetcher import HttpFetcher
from dnscache import DnsCache
from flowcontrol import SiteProfile
from connpool import BaseConnection, ConnectionPool

__all__ = ['HttpRequest', 'REDIRECT_INFINITE', 'REDIRECT_REFUSE',
           'HttpResponse', 'HttpClient', 'HttpFetcher',
           'DnsCache', 'SiteProfile',
           'UnsupportedProtocol', 'TooManyRedirects', 'ConnectError',
           'ProxyResolveError', 'HostResolveError', 'OperationTimeoutError',
           'BaseConnection', 'ConnectionPool',
           'Request', 'urlopen',]

Request = HttpRequest

def urlopen(url_or_request, data_or_reader=None, timeout=None):
    if issubclass(type(url_or_request), HttpRequest):
        request = url_or_request
    else:
        request = HttpRequest(str(url_or_request), data_or_reader)
        
    if timeout:
        SiteProfile.get(request.hostname).timeout = timeout
        
    return HttpClient().perform(request)