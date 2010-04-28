#!/usr/bin/env python
import sys
import os, os.path
import string, binascii
import logging

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from httplib import HTTPMessage
from urlparse import urlparse

import pycurl

REDIRECT_REFUSE     = 0
REDIRECT_INFINITE   = -1

class HttpRequest(object):
    def __init__(self, url, data_or_reader=None, headers=None,
                 origin_req_host=None, unverifiable=False,
                 referer=None, user_agent=None,
                 cookie_or_file=None, accept_encoding=None,
                 ssl_verify_peer=False, ssl_verify_host=False,
                 auto_referer=True, follow_location=True,
                 max_redirects=REDIRECT_INFINITE,
                 proxy_host=None, proxy_type='http'):
        
        self.url = url
        self.data_or_reader = data_or_reader
        self.referer = referer
        self.user_agent = user_agent
        self.cookie_or_file = cookie_or_file
        self.accept_encoding = accept_encoding
        self.ssl_verify_peer = ssl_verify_peer
        self.ssl_verify_host = ssl_verify_host
        self.auto_referer = auto_referer
        self.follow_location = follow_location
        self.max_redirects = max_redirects
        self.set_proxy(proxy_host, proxy_type)
        
    def get_method(self):
        '''Return a string indicating the HTTP request method. '''
        return 'GET' if self.data_or_reader else 'POST'
    
    def has_data(self):
        '''Return whether the instance has a non-None data.'''
        return self.data_or_reader != None
    
    def get_data(self):
        '''Return the instance's data. '''
        return self.data_or_reader
    
    def get_full_url(self):
        '''Return the URL given in the constructor.'''
        return self.url
    
    def get_type(self):
        '''Return the type of the URL -- also known as the scheme. '''
        return urlparse(self.url).scheme
        
    def get_host(self):
        '''Return the host to which a connection will be made.'''
        return urlparse(self.url).hostname
        
    def get_selector(self):
        '''Return the selector -- the part of the URL that is sent to the server.'''
        return urlparse(self.url).path

    def set_proxy(self, host, type='http'):
        '''
        Prepare the request by connecting to a proxy server.
        The host and type will replace those of the instance,
        and the instance's selector will be the original URL given in the constructor.
        '''
        PROXY_TYPES = {
            'http': pycurl.PROXYTYPE_HTTP,
            'sock4': pycurl.PROXYTYPE_SOCKS4,
            'sock5': pycurl.PROXYTYPE_SOCKS5,
        }
                
        self.proxy_auth = None
        
        try:
            o = urlparse(host)
            
            if o and o.netloc:
                host = o.netloc
                type = o.scheme
                self.proxy_auth = '%s:%s' % (o.username, o.password)
        except:
            pass
        
        self.proxy_host = host
        self.proxy_type = PROXY_TYPES.get(type, pycurl.PROXYTYPE_HTTP)        

class HttpResponse(object):
    def __init__(self, client, request):
        self.client = client
        self.request = request
        
        self.cached_headers = None
        
    def __getattr__(self, name):
        if name in ['__iter__', 'next', 'isatty', 'seek', 'tell',
                    'read', 'readline', 'readlines', 'truncate',
                    'write', 'writelines', 'flush']:
            return getattr(self.client.body, name)
            
        raise AttributeError(name)
    
    def __getitem__(self, key):
        return self.client.curl.getinfo(key)
    
    def close(self):
        pass
                
    def geturl(self):
        '''the effective URL'''
        return self[pycurl.EFFECTIVE_URL]
        
    @property
    def code(self):
        '''the HTTP or FTP code'''
        return self[pycurl.RESPONSE_CODE]

    @property
    def headers(self):
        if not self.cached_headers:
            self.client.header.readline() # eat the first line 'HTTP/1.1 200 OK'
            self.cached_headers = HTTPMessage(self.client.header)
            self.client.header.seek(0)
            
        return self.cached_headers
    
    info = headers
    
# = Time = 
#
# An overview of the six time values available from curl_easy_getinfo()
# 
# curl_easy_perform()
#     |
#     |--NAMELOOKUP
#     |--|--CONNECT
#     |--|--|--APPCONNECT
#     |--|--|--|--PRETRANSFER
#     |--|--|--|--|--STARTTRANSFER
#     |--|--|--|--|--|--TOTAL
#     |--|--|--|--|--|--REDIRECT
        
    @property
    def namelookup_time(self):
        '''
        The time it took from the start until the name resolving was completed.
        '''
        return self[pycurl.NAMELOOKUP_TIME]
        
    @property
    def connect_time(self):
        '''
        The time it took from the start until the connect to
        the remote host (or proxy) was completed.
        '''
        return self[pycurl.CONNECT_TIME]
        
    @property
    def appconnect_time(self):
        '''
        The time it took from the start until the SSL connect/handshake
        with the remote host was completed. (Added in in 7.19.0)
        '''
        return self[pycurl.APPCONNECT_TIME]

    @property
    def pretransfer_time(self):
        '''
        The time it took from the start until the file transfer is just about to begin.
        This includes all pre-transfer commands and negotiations that are specific
        to the particular protocol(s) involved.
        '''
        return self[pycurl.PRETRANSFER_TIME]
        
        
    @property
    def starttransfer_time(self):
        '''
        The time it took from the start until the first byte is just about to be transferred.
        '''
        return self[pycurl.STARTTRANSFER_TIME]
        
    @property
    def total_time(self):
        '''
        The total time in seconds for the previous transfer,
        including name resolving, TCP connect etc.
        '''
        return self[pycurl.TOTAL_TIME]
                
    @property
    def redirect_time(self):
        '''
        The time it took for all redirection steps include name lookup,
        connect, pretransfer and transfer before final transaction was started.
        So, this is zero if no redirection took place.
        '''
        return self[pycurl.REDIRECT_TIME]
        
    @property
    def redirect_count(self):
        '''
        The total number of redirections that were actually followed.
        '''
        return self[pycurl.REDIRECT_COUNT]
    
    @property
    def redirect_url(self):
        '''
        The URL a redirect would take you to.
        '''
        return self[pycurl.REDIRECT_URL]
        
class HttpClient(object):
    INFOTYPE_NAMES = {
        pycurl.INFOTYPE_DATA_IN: 'data:in',
        pycurl.INFOTYPE_DATA_OUT: 'data:out',
        pycurl.INFOTYPE_HEADER_IN: 'header:in',
        pycurl.INFOTYPE_HEADER_OUT: 'header:out',
        pycurl.INFOTYPE_SSL_DATA_IN: 'ssl:in',
        pycurl.INFOTYPE_SSL_DATA_OUT: 'ssl:out',
        pycurl.INFOTYPE_TEXT: 'text',
    }
    
    def __init__(self):
        self.curl = pycurl.Curl()
        
        self.curl.setopt(pycurl.VERBOSE, 1)
        self.curl.setopt(pycurl.DEBUGFUNCTION, self.log)                 
        
        self.header = StringIO()
        self.body = StringIO()        
        
    def __del__(self):
        self.curl.close()
        self.header.close()
        self.body.close()
        
    def log(self, type, msg):
        if [c for c in msg if c not in string.printable]:
            logging.debug("%s: %s", self.INFOTYPE_NAMES[type], binascii.hexlify(msg))
        else:
            logging.debug("%s: %s", self.INFOTYPE_NAMES[type], msg)
                    
    def get(self, url, progress_callback=None):
        return self.perform(HttpRequest(url), progress_callback)
        
    def post(self, url, data_or_reader, progress_callback=None):
        return self.perform(HttpRequest(url, data_or_reader), progress_callback)
        
    def perform(self, request, progress_callback=None):
        self.header.seek(0)
        self.body.seek(0)

        self.curl.setopt(pycurl.URL, request.url)
        self.curl.setopt(pycurl.HEADERFUNCTION, lambda buf: self.header.write(buf))
        self.curl.setopt(pycurl.WRITEFUNCTION, lambda buf: self.body.write(buf))
        
        if request.data_or_reader:
            pass
        else:
            self.curl.setopt(pycurl.HTTPGET, 1)
        
        if progress_callback:
            self.curl.setopt(pycurl.NOPROGRESS, 0)
            self.curl.setopt(pycurl.PROGRESSFUNCTION, progress_callback)
        else:
            self.curl.setopt(pycurl.NOPROGRESS, 1)
            
        if request.referer:
            self.curl.setopt(pycurl.REFERER, request.referer)

        if request.user_agent:
            self.curl.setopt(pycurl.USERAGENT, request.user_agent)
            
        if request.cookie_or_file:
            if os.path.exists(request.cookie_or_file):
                self.curl.setopt(pycurl.COOKIEFILE, request.cookie_or_file)
            else:
                self.curl.setopt(pycurl.COOKIE, request.cookie_or_file)
                
        if request.accept_encoding:
            self.curl.setopt(pycurl.ENCODING, request.accept_encoding)
            self.curl.setopt(pycurl.HTTP_CONTENT_DECODING, 1)
        else:
            self.curl.setopt(pycurl.HTTP_CONTENT_DECODING, 0)
            
        if request.ssl_verify_peer:
            self.curl.setopt(pycurl.SSL_VERIFYPEER, 1)
            
            # TODO: setup the CA path
        else:
            self.curl.setopt(pycurl.SSL_VERIFYPEER, 0)
            
        if request.ssl_verify_host:
            # the certificate must indicate that the server is the server
            # to which you meant to connect, or the connection fails.
            self.curl.setopt(pycurl.SSL_VERIFYHOST, 2)
        else:
            self.curl.setopt(pycurl.SSL_VERIFYHOST, 0)
            
        self.curl.setopt(pycurl.AUTOREFERER, 1 if request.auto_referer else 0)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1 if request.follow_location else 0)
        self.curl.setopt(pycurl.MAXREDIRS, request.max_redirects)
        
        if request.proxy_host:
            self.curl.setopt(pycurl.PROXY, request.proxy_host)
            self.curl.setopt(pycurl.PROXYTYPE, request.proxy_type)
            
            if request.proxy_auth:
                self.curl.setopt(pycurl.PROXYUSERPWD, request.proxy_auth)
        else:
            self.curl.setopt(pycurl.PROXY, "")

        self.curl.perform()
        
        self.header.seek(0)
        self.body.seek(0)
        
        return HttpResponse(self, request)
        
Request = HttpRequest

def urlopen(url_or_request, data_or_reader=None):
    if issubclass(type(url_or_request), HttpRequest):
        request = url_or_request
    else:
        request = HttpRequest(str(url_or_request), data_or_reader)
        
    return HttpClient().perform(request)