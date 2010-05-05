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
        
        raise exc(code, msg) if exc else URLError(msg)

class TooManyRedirects(PycurlError):
    pass

PYCURL_ERRORS = {
    pycurl.E_TOO_MANY_REDIRECTS: TooManyRedirects,
}
