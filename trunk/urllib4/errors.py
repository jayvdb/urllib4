#!/usr/bin/env python

from urllib2 import URLError

import pycurl

class PycurlError(URLError):
    def __init__(self, code, msg):        
        self.code = code
        self.msg = msg
        
    def __str__(self):
        return 'Pycurl Error %s: %s' % (self.code, self.msg)
        
    @staticmethod
    def convert(code, msg):
        exc = PYCURL_ERRORS.get(code)
        
        raise exc(code, msg) if exc else PycurlError(code, msg)

class UnsupportedProtocol(PycurlError):
    pass

class DnsResolveError(PycurlError):
    pass

class ProxyResolveError(DnsResolveError):
    pass

class HostResolveError(DnsResolveError):
    pass

class ConnectError(PycurlError):
    pass

class OperationTimeoutError(PycurlError):
    pass

class TooManyRedirects(PycurlError):
    pass

PYCURL_ERRORS = {
    pycurl.E_UNSUPPORTED_PROTOCOL: UnsupportedProtocol,
    pycurl.E_COULDNT_RESOLVE_PROXY: ProxyResolveError,
    pycurl.E_COULDNT_RESOLVE_HOST: HostResolveError,
    pycurl.E_COULDNT_CONNECT: ConnectError,
    pycurl.E_OPERATION_TIMEOUTED: OperationTimeoutError,
    pycurl.E_TOO_MANY_REDIRECTS: TooManyRedirects,    
}
