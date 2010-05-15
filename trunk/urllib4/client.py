#!/usr/bin/env python
import string, binascii
import logging

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
    
try:
    from gurl import Url
    urlparse = Url
except ImportError:
    from urlparse import urlparse
    
import urllib

import pycurl

from request import HttpRequest
from response import HttpResponse
from errors import PycurlError
from flowcontrol import SiteProfile

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
    
    def __init__(self, dnscache=None, profile=None):        
        self.dnscache = dnscache
        self.profile = profile

        self.curl = pycurl.Curl()
                
        self.header = StringIO()
        self.body = StringIO()
                
    def __del__(self):
        self.curl.close()
        self.header.close()
        self.body.close()        
        
    def _log(self, type, msg):
        if [c for c in msg if c not in string.printable]:
            logging.debug("%s: %s", self.INFOTYPE_NAMES[type], binascii.hexlify(msg))
        else:
            logging.debug("%s: %s", self.INFOTYPE_NAMES[type], msg)
            
    def _cleanup(self):
        self.curl.setopt(pycurl.DEBUGFUNCTION, lambda type, msg: None)
        self.curl.setopt(pycurl.HEADERFUNCTION, lambda buf: None)
        self.curl.setopt(pycurl.WRITEFUNCTION, lambda buf: None)
        self.curl.setopt(pycurl.READFUNCTION, lambda size: None)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, lambda download_total, downloaded, upload_total, uploaded: None)
        self.curl.setopt(pycurl.IOCTLFUNCTION, lambda cmd: None)
        
    def _apply_debug_setting(self, request):
        self.curl.setopt(pycurl.VERBOSE, 1)
        self.curl.setopt(pycurl.DEBUGFUNCTION, self._log)
        
    def _apply_progress_setting(self, progress_callback):
        if progress_callback:
            self.curl.setopt(pycurl.NOPROGRESS, 0)
            self.curl.setopt(pycurl.PROGRESSFUNCTION, progress_callback)
        else:
            self.curl.setopt(pycurl.NOPROGRESS, 1)
        
    def _apply_request_setting(self, request):        
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
                
    def _apply_dnscache_setting(self, request):
        o = urlparse(request.url)
        
        if self.dnscache:
            addresses = self.dnscache.get(o.hostname)
            
            if addresses:
                request.add_header('host', o.hostname)
                
                return o.hostname, request.url.replace(o.hostname, addresses[0])
                
        return o.hostname, request.url
                
    def _apply_network_setting(self, request):
        if request.interface:
            self.curl.setopt(pycurl.INTERFACE, request.interface)

        if request.local_port:
            self.curl.setopt(pycurl.LOCALPORT, request.local_port)
            
        if request.local_port_range:
            self.curl.setopt(pycurl.LOCALPORTRANGE, request.local_port_range)
            
        if request.tcp_nodelay:
            self.curl.setopt(pycurl.TCP_NODELAY, request.tcp_nodelay)
            
    def _apply_ssl_setting(self, request):
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
            
    def _apply_auth_setting(self, request):
        if request.username and request.password:
            if request.realm:
                self.curl.setopt(pycurl.USERPWD, "%s/%s:%s" % (request.realm, request.username, request.password))
            else:
                self.curl.setopt(pycurl.USERPWD, "%s:%s" % (request.username, request.password))
            
        self.curl.setopt(pycurl.HTTPAUTH, request.http_auth_mode)
        
    def _apply_redirect_setting(self, request):
        self.curl.setopt(pycurl.AUTOREFERER, 1 if request.auto_referer else 0)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1 if request.follow_location else 0)
        self.curl.setopt(pycurl.MAXREDIRS, request.max_redirects)
        
    def _apply_http_setting(self, request):                       
        if request.http_version:
            self.curl.setopt(pycurl.HTTP_VERSION, request.http_version)
        
        if request.http_custom_request:
            self.curl.setopt(pycurl.CUSTOMREQUEST, request.http_custom_request)
                    
        if request.referer:
            self.curl.setopt(pycurl.REFERER, request.referer)

        if request.user_agent:
            self.curl.setopt(pycurl.USERAGENT, request.user_agent)

        if request.accept_encoding:
            self.curl.setopt(pycurl.ENCODING, request.accept_encoding)
            self.curl.setopt(pycurl.HTTP_CONTENT_DECODING, 1)
        else:
            self.curl.setopt(pycurl.HTTP_CONTENT_DECODING, 0)
        
        if request.cookie_or_file:
            if os.path.exists(request.cookie_or_file):
                self.curl.setopt(pycurl.COOKIEFILE, request.cookie_or_file)
            else:
                if issubclass(type(request.cookie_or_file), dict):
                    cookie = ';'.join(['%s=%s' % (k, v) for k, v in request.cookie_or_file.items()])
                else:
                    cookie = request.cookie_or_file
                    
                self.curl.setopt(pycurl.COOKIE, cookie)
        
    def _apply_proxy_setting(self, request):
        if request.proxy_host:
            self.curl.setopt(pycurl.PROXY, request.proxy_host)
            self.curl.setopt(pycurl.PROXYTYPE, request.proxy_type)
            
            if request.proxy_auth:
                self.curl.setopt(pycurl.PROXYUSERPWD, request.proxy_auth)
                
            self.curl.setopt(pycurl.PROXYAUTH, request.proxy_auth_mode)
                
        else:
            self.curl.setopt(pycurl.PROXY, "")

    def get(self, url, progress_callback=None):
        return self.perform(HttpRequest(url), progress_callback)
        
    def post(self, url, data_or_reader, progress_callback=None):
        return self.perform(HttpRequest(url, data_or_reader), progress_callback)
        
    def perform(self, request, progress_callback=None):
        self.header.seek(0)
        self.body.seek(0)
        
        self._apply_debug_setting(request)
        self._apply_progress_setting(progress_callback)
        
        domain, url = self._apply_dnscache_setting(request)
        
        profile = self.profile or SiteProfile.get(domain)
        profile.apply(self.curl)
        
        self.curl.setopt(pycurl.URL, url)
        
        self._apply_request_setting(request)
        self._apply_network_setting(request)            
        self._apply_http_setting(request)
        self._apply_ssl_setting(request)
        self._apply_redirect_setting(request)        
        self._apply_auth_setting(request)        
        self._apply_proxy_setting(request)

        try:
            self.curl.perform()
        except pycurl.error, (code, msg):
            PycurlError.convert(code, msg)
        
        self.header.seek(0)
        self.body.seek(0)
        
        self._cleanup()
                
        return HttpResponse(self, request)
        