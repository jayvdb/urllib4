#!/usr/bin/env python
import sys
import os, os.path
import string, binascii
import logging

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import urllib, urllib2
from urlparse import urlparse

import pycurl

REDIRECT_REFUSE     = 0
REDIRECT_INFINITE   = -1

class HttpRequest(object):    
    def __init__(self, url, data_or_reader=None, headers={}, 
                 origin_req_host=None, unverifiable=False,
                 referer=None, user_agent=None, 
                 interface=None, local_port=None, local_port_range=None, tcp_nodelay=None,
                 cookie_or_file=None, accept_encoding=None,
                 ssl_verify_peer=False, ssl_verify_host=False,
                 auto_referer=True, follow_location=True, max_redirects=REDIRECT_INFINITE,
                 http_version='last', http_custom_request=None,
                 realm=None, username=None, password=None, http_auth_mode=['anysafe'], 
                 proxy_host=None, proxy_type='http', proxy_auth_mode=['anysafe']):
        
        self.url = url
        self.data_or_reader = data_or_reader
        self.headers = headers
        self.referer = referer
        self.user_agent = user_agent
        self.interface = interface
        self.local_port = local_port
        self.local_port_range = local_port_range
        self.tcp_nodelay = tcp_nodelay
        self.cookie_or_file = cookie_or_file
        self.accept_encoding = accept_encoding
        self.ssl_verify_peer = ssl_verify_peer
        self.ssl_verify_host = ssl_verify_host
        self.auto_referer = auto_referer
        self.follow_location = follow_location
        self.max_redirects = max_redirects
        self.set_http_version(http_version)
        self.http_custom_request = http_custom_request
        self.username = username
        self.password = password
        self.http_auth_mode = self.convert_auth_mode(http_auth_mode)        
        self.set_proxy(proxy_host, proxy_type, proxy_auth_mode)
        
    def convert_auth_mode(self, modes):
        AUTH_MODES = {
            'basic': pycurl.HTTPAUTH_BASIC,             # HTTP Basic authentication.
            'digest': pycurl.HTTPAUTH_DIGEST,           # HTTP Digest authentication.
            'negotiate': pycurl.HTTPAUTH_GSSNEGOTIATE,  # HTTP GSS-Negotiate authentication.
            'ntlm': pycurl.HTTPAUTH_NTLM,               # HTTP NTLM authentication. 
            'any': pycurl.HTTPAUTH_ANY,
            'anysafe': pycurl.HTTPAUTH_ANYSAFE,
            'none': pycurl.HTTPAUTH_NONE,
        }
        
        if not issubclass(type(modes), list):
            modes = [modes]
            
        auth_mode = 0
            
        for mode in modes:
            auth_mode |= AUTH_MODES.get(mode.lower(), 0)
            
        return auth_mode
    
    def get_method(self):
        '''Return a string indicating the HTTP request method. '''
        return 'GET' if self.has_data() else 'POST'
    
    def add_data(self, data):
        '''Set the Request data to data.'''
        self.data_or_reader = data
    
    def has_data(self):
        '''Return whether the instance has a non-None data.'''
        return self.data_or_reader is not None
    
    def get_data(self):
        '''Return the instance's data. '''
        return self.data_or_reader
    
    def add_header(self, key, val):
        '''Add another header to the request.'''
        self.headers[key.capitalize()] = val
        
    def has_header(self, header):
        '''Return whether the instance has the named header.'''
        return self.headers.has_key(header)
    
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

    def set_proxy(self, host, type='http', auth_mode='basic'):
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
        self.proxy_type = PROXY_TYPES.get(type.lower(), pycurl.PROXYTYPE_HTTP)
        self.proxy_auth_mode = self.convert_auth_mode(auth_mode)
        
    def set_http_version(self, version):
        HTTP_VERSIONS = {
            '1.0': pycurl.CURL_HTTP_VERSION_1_0,
            '1.1': pycurl.CURL_HTTP_VERSION_1_1,
            'last': pycurl.CURL_HTTP_VERSION_LAST,
            'none': pycurl.CURL_HTTP_VERSION_NONE,
        }
        
        self.http_version = HTTP_VERSIONS.get(version.lower(), pycurl.CURL_HTTP_VERSION_LAST)

class HttpResponse(object):
    BUILDIN_FIELDS = {
            'url': pycurl.EFFECTIVE_URL,
            'code': pycurl.RESPONSE_CODE,
            'connect_code': pycurl.HTTP_CONNECTCODE,
                
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
                    
            'namelookup_time': pycurl.NAMELOOKUP_TIME,
            'connect_time': pycurl.CONNECT_TIME,
            #'appconnect_time': pycurl.APPCONNECT_TIME,
            'pretransfer_time': pycurl.PRETRANSFER_TIME,
            'starttransfer_time': pycurl.STARTTRANSFER_TIME,
            'total_time': pycurl.TOTAL_TIME,
            'redirect_time': pycurl.REDIRECT_TIME,
            
            'redirect_count': pycurl.REDIRECT_COUNT,
            'redirect_url': pycurl.REDIRECT_URL,
            
            'size_upload': pycurl.SIZE_UPLOAD,
            'size_download': pycurl.SIZE_DOWNLOAD,
            'speed_upload': pycurl.SPEED_UPLOAD,
            'speed_download': pycurl.SPEED_DOWNLOAD,
            'header_size': pycurl.HEADER_SIZE,
            'request_size': pycurl.REQUEST_SIZE,
            
            'ssl_verify_result': pycurl.SSL_VERIFYRESULT,
            'ssl_engines': pycurl.SSL_ENGINES,
            
            'content_length_upload': pycurl.CONTENT_LENGTH_UPLOAD,
            'content_length_download': pycurl.CONTENT_LENGTH_DOWNLOAD,
            'content_type': pycurl.CONTENT_TYPE,
            
            'os_errno': pycurl.OS_ERRNO,
            'num_connects': pycurl.NUM_CONNECTS,
            #'primary_ip': pycurl.PRIMARY_IP,
            
            'cookie_list': pycurl.COOKIELIST,
            'last_socket': pycurl.LASTSOCKET,
        }
            
    def __init__(self, client, request):
        self.client = client
        self.request = request
        
        self.cached_headers = None
        
    def __getattr__(self, name):

        if name in ['__iter__', 'next', 'isatty', 'seek', 'tell',
                    'read', 'readline', 'readlines', 'truncate',
                    'write', 'writelines', 'flush']:
            return getattr(self.client.body, name)
        elif self.BUILDIN_FIELDS.has_key(name):
            value = self.BUILDIN_FIELDS[name]
            
            if callable(value):
                return value()
            elif type(value) == tuple:
                field, convert = value
                
                return convert(self.client.curl.getinfo(field))
            else:
                return self.client.curl.getinfo(value)
            
        raise AttributeError(name)
    
    def close(self):
        pass
                
    def geturl(self):
        return self.url

    @property
    def headers(self):
        from httplib import HTTPMessage
        
        if not self.cached_headers:
            self.client.header.readline() # eat the first line 'HTTP/1.1 200 OK'
            self.cached_headers = HTTPMessage(self.client.header)
            self.client.header.seek(0)
            
        return self.cached_headers
    
    info = headers
        
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
            if callable(request.data_or_reader):
                self.curl.setopt(pycurl.POST, 1)
                self.curl.setopt(pycurl.READFUNCTION, request.data_or_reader)
            else:
                if type(request.data_or_reader) == dict:
                    self.curl.setopt(pycurl.POSTFIELDS, urllib.urlencode(request.data_or_reader))
                elif type(request.data_or_reader) == list:
                    self.curl.setopt(pycurl.HTTPPOST, request.data_or_reader)
                else:
                    self.curl.setopt(pycurl.POSTFIELDS, str(request.data_or_reader))
        else:
            self.curl.setopt(pycurl.HTTPGET, 1)
            
        self.curl.setopt(pycurl.HTTPHEADER, ["%s: %s" % (key.capitalize(), value) for key, value in request.headers.items()])
        
        if progress_callback:
            self.curl.setopt(pycurl.NOPROGRESS, 0)
            self.curl.setopt(pycurl.PROGRESSFUNCTION, progress_callback)
        else:
            self.curl.setopt(pycurl.NOPROGRESS, 1)
            
        if request.referer:
            self.curl.setopt(pycurl.REFERER, request.referer)

        if request.user_agent:
            self.curl.setopt(pycurl.USERAGENT, request.user_agent)
            
        if request.interface:
            self.curl.setopt(pycurl.INTERFACE, request.interface)

        if request.local_port:
            self.curl.setopt(pycurl.LOCALPORT, request.local_port)
            
        if request.local_port_range:
            self.curl.setopt(pycurl.LOCALPORTRANGE, request.local_port_range)
            
        if request.tcp_nodelay:
            self.curl.setopt(pycurl.TCP_NODELAY, request.tcp_nodelay)
        
        if request.cookie_or_file:
            if os.path.exists(request.cookie_or_file):
                self.curl.setopt(pycurl.COOKIEFILE, request.cookie_or_file)
            else:
                if issubclass(type(request.cookie_or_file), dict):
                    cookie = ';'.join(['%s=%s' % (k, v) for k, v in request.cookie_or_file.items()])
                else:
                    cookie = request.cookie_or_file
                    
                self.curl.setopt(pycurl.COOKIE, cookie)
                
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
        
        if request.username and request.password:
            if request.realm:
                self.curl.setopt(pycurl.USERPWD, "%s/%s:%s" % (request.realm, request.username, request.password))
            else:
                self.curl.setopt(pycurl.USERPWD, "%s:%s" % (request.username, request.password))
            
        self.curl.setopt(pycurl.HTTPAUTH, request.http_auth_mode)
        
        if request.http_version:
            self.curl.setopt(pycurl.HTTP_VERSION, request.http_version)
        
        if request.http_custom_request:
            self.curl.setopt(pycurl.CUSTOMREQUEST, request.http_custom_request)
        
        if request.proxy_host:
            self.curl.setopt(pycurl.PROXY, request.proxy_host)
            self.curl.setopt(pycurl.PROXYTYPE, request.proxy_type)
            
            if request.proxy_auth:
                self.curl.setopt(pycurl.PROXYUSERPWD, request.proxy_auth)
                
            self.curl.setopt(pycurl.PROXYAUTH, request.proxy_auth_mode)
                
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