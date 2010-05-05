#!/usr/bin/env python
from request import HttpRequest, REDIRECT_INFINITE, REDIRECT_REFUSE
from response import HttpResponse
from errors import TooManyRedirects
from client import HttpClient
from fetcher import HttpFetcher

__all__ = ['HttpRequest', 'REDIRECT_INFINITE', 'REDIRECT_REFUSE',
           'HttpResponse', 'HttpClient', 'HttpFetcher',
           'TooManyRedirects',
           'Request', 'urlopen']

Request = HttpRequest

def urlopen(url_or_request, data_or_reader=None):
    if issubclass(type(url_or_request), HttpRequest):
        request = url_or_request
    else:
        request = HttpRequest(str(url_or_request), data_or_reader)
        
    return HttpClient().perform(request)