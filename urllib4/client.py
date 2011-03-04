#!/usr/bin/env python
import sys, os, os.path
import string, binascii
import logging
from hashlib import md5
import socket
from functools import partial

try:
    from gurl import Url
    urlparse = Url
except ImportError:
    from urlparse import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import urllib

import pycurl

from request import HttpRequest
from response import HttpResponse
from errors import PycurlError
from pipeline import get_default_pipeline
from flowcontrol import SiteProfile
from guessencoding import guess_encoding, guess_charset

PROGRESS_CALLBACK_CONTINUE = 0
PROGRESS_CALLBACK_ABORT = 1

READ_CALLBACK_ABORT = pycurl.READFUNC_ABORT

"""
def debug_callback(type, msg):
    pass

def header_callback(buf):
    return len(buf)

def write_callback(buf):
    return len(buf) # number of characters written

def read_callback(size):
    return <str> or READ_CALLBACK_ABORT

def progress_callback(download_total, downloaded, upload_total, uploaded):
    return PROGRESS_CALLBACK_CONTINUE or PROGRESS_CALLBACK_ABORT

def ioctl_callback(cmd):
    return <status>
"""

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

    def __init__(self, dnscache=None, pagecache=None, pipeline=None,
                 profile=None, guess_encoding=None, dump_raw_data=False):
        self.dnscache = dnscache
        self.pagecache = pagecache
        self.pipeline = pipeline
        self.profile = profile
        self.guess_encoding = guess_encoding
        self.dump_raw_data = dump_raw_data

        self.curl = pycurl.Curl()

        self.header = []
        self.body = []
        self.file = None

    def __del__(self):
        self.curl.close()

    def _log(self, type, msg):
        if self.dump_raw_data:
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

        if hasattr(pycurl, 'OPENSOCKETFUNCTION'):
            self.curl.setopt(pycurl.OPENSOCKETFUNCTION, lambda family, type, proto: None)

    def _apply_debug_setting(self, request):
        self.curl.setopt(pycurl.VERBOSE, 1)
        self.curl.setopt(pycurl.DEBUGFUNCTION, self._log)

    def _apply_progress_setting(self, progress_callback):
        if progress_callback:
            self.curl.setopt(pycurl.NOPROGRESS, 0)
            self.curl.setopt(pycurl.PROGRESSFUNCTION, progress_callback)
        else:
            self.curl.setopt(pycurl.NOPROGRESS, 1)

    def _header_callback(self, buf):
        self.header.append(buf)

    def _write_callback(self, buf):
        if self.file:
            self.file.write(buf)
        else:
            self.body.append(buf)

    def _apply_request_setting(self, request):
        self.curl.setopt(pycurl.HEADERFUNCTION, self._header_callback)
        self.curl.setopt(pycurl.WRITEFUNCTION, self._write_callback)

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

            if request.method not in ['POST', None]:
                self.curl.setopt(pycurl.CUSTOMREQUEST, request.method)
        else:
            if request.method == 'HEAD':
                self.curl.setopt(pycurl.CURLOPT_NOBODY, 1)
            elif request.method not in ['GET', None]:
                self.curl.setopt(pycurl.CUSTOMREQUEST, request.method)
            else:
                self.curl.setopt(pycurl.HTTPGET, 1)

        self.curl.setopt(pycurl.HTTPHEADER, ["%s: %s" % (key, value) for key, value in request.headers.items()])

    def _apply_dnscache_setting(self, request, connect_callback=None):
        o = urlparse(request.url)

        if self.dnscache:
            address = self.dnscache.get(o.hostname)[0]
        elif connect_callback:
            address = socket.gethostbyname(o.hostname)

            connect_callback(request, address)
        else:
            address = None

        if address:
            request.add_header('host', o.hostname)

            return o.hostname, request.url.replace(o.hostname, address)

        return o.hostname, request.url

    def _apply_timeout_setting(self, request):
        if request.session_timeout:
            self.curl.setopt(pycurl.TIMEOUT, request.session_timeout)

        if request.connect_timeout:
            self.curl.setopt(pycurl.CONNECTTIMEOUT, request.connect_timeout)

        self.curl.setopt(pycurl.NOSIGNAL, 1 if request.no_signal else 0)

    @staticmethod
    def _create_socket(request, family, type, proto):
        s = socket.socket(family, type, proto)

        if request.sendbuf:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, request.sendbuf)

        if request.recvbuf:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, request.recvbuf)

        return s

    def _apply_network_setting(self, request):
        if hasattr(pycurl, 'OPENSOCKETFUNCTION'):
            self.curl.setopt(pycurl.OPENSOCKETFUNCTION, partial(self._create_socket, request))

        if request.interface:
            self.curl.setopt(pycurl.INTERFACE, request.interface)

        if request.local_port:
            self.curl.setopt(pycurl.LOCALPORT, request.local_port)

        if request.local_port_range:
            self.curl.setopt(pycurl.LOCALPORTRANGE, request.local_port_range)

        if request.tcp_nodelay:
            self.curl.setopt(pycurl.TCP_NODELAY, request.tcp_nodelay)

        if request.bufsize:
            self.curl.setopt(pycurl.BUFFERSIZE, request.bufsize)

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

        if request.range:
            self.curl.setopt(pycurl.RANGE, "%d-%d" % tuple(request.range))

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

    def _apply_pagecache_setting(self, request):
        if self.pagecache:
            self.page = self.pagecache.get(request.url, request.get_method())

            if self.page.etag:
                request.add_header('If-None-Match', '"%s"' % self.page.etag)

            if self.page.last_modified:
                request.add_header('If-Modified-Since', self.page.last_modified)

    def _update_pagecache_setting(self, response):
        if self.pagecache and response.code == 200:
            hash = md5()

            for data in self.body:
                hash.update(data)

            etag = response.headers.get('ETag', None)

            if etag and etag[0] == '"' and etag[-1] == '"':
                etag = etag[1:-1]

            if self.page.md5 == hash.hexdigest():
                response.code = 304

            self.page.md5 = hash.hexdigest()
            self.page.etag = etag
            self.page.last_modified = response.headers.get('Last-Modified', None)
            self.page.update()

    @property
    def status(self):
        from httplib import HTTPMessage

        header = StringIO(''.join(self.header))
        try:
            return header.readline()
        finally:
            header.close()

    @property
    def headers(self):
        from httplib import HTTPMessage

        header = StringIO(''.join(self.header))
        try:
            header.readline() # eat the first line 'HTTP/1.1 200 OK'
            return HTTPMessage(header)
        finally:
            header.close()

    def close(self):
        self.curl.close()

    def get(self, url, progress_callback=None, *args, **kwds):
        return self.perform(HttpRequest(url, *args, **kwds), progress_callback)

    def async_get(self, url, finish_callback, pipeline=None, progress_callback=None, *args, **kwds):
        return self.async_perform(request=HttpRequest(url, *args, **kwds),
                                  finish_callback=finish_callback,
                                  pipeline=pipeline,
                                  progress_callback=progress_callback)

    def post(self, url, data_or_reader, progress_callback=None, *args, **kwds):
        return self.perform(HttpRequest(url, data_or_reader, *args, **kwds), progress_callback)

    def async_post(self, url, data_or_reader, finish_callback, pipeline=None, progress_callback=None, *args, **kwds):
        return self.async_perform(request=HttpRequest(url, data_or_reader, *args, **kwds),
                                  finish_callback=finish_callback,
                                  pipeline=pipeline,
                                  progress_callback=progress_callback)

    def download(self, url, file, progress_callback=None, *args, **kwds):
        self.file = file

        return self.perform(HttpRequest(url, *args, **kwds), progress_callback)

    def async_download(self, url, file, finish_callback, pipeline=None, progress_callback=None, *args, **kwds):
        self.file = file

        def onfinish(*args, **kwds):
            self.file.close()

            finish_callback(*args, **kwds)

        return self.async_perform(request=HttpRequest(url, *args, **kwds),
                                  finish_callback=onfinish,
                                  pipeline=pipeline,
                                  progress_callback=progress_callback)

    def prepare(self, request, progress_callback=None, connect_callback=None):
        request.client = self

        self.header = []
        self.body = []

        self._apply_debug_setting(request)
        self._apply_progress_setting(progress_callback)

        domain, request.url = self._apply_dnscache_setting(request, connect_callback)

        profile = self.profile or SiteProfile.get(domain)
        profile.apply(self.curl)

        self.curl.setopt(pycurl.URL, request.url)

        self._apply_pagecache_setting(request)
        self._apply_request_setting(request)
        self._apply_timeout_setting(request)
        self._apply_network_setting(request)
        self._apply_http_setting(request)
        self._apply_ssl_setting(request)
        self._apply_redirect_setting(request)
        self._apply_auth_setting(request)
        self._apply_proxy_setting(request)

    def postmortem(self, response):
        self.file = None

        self._update_pagecache_setting(response)

        if self.guess_encoding is not None:
            charset = guess_charset(response.headers.get("Content-Type"))

            if type(self.guess_encoding) == str:
                self.guess_encoding = [self.guess_encoding, charset]
            elif type(self.guess_encoding) == list:
                self.guess_encoding += [charset]
            else:
                self.guess_encoding = [charset]

            text, response.encoding, response.declared_encoding = \
                guess_encoding(''.join(self.body), self.guess_encoding + [charset])

        return response

    def perform(self, request, progress_callback=None, connect_callback=None):
        self.prepare(request, progress_callback, connect_callback)

        response = HttpResponse(self, request)

        try:
            self.curl.perform()
        except pycurl.error, (code, msg):
            PycurlError.convert(code, msg, response)
        finally:
            self._cleanup()

        return self.postmortem(response)

    def async_perform(self, request, finish_callback, pipeline=None, progress_callback=None):
        if pipeline is None:
            pipeline = self.pipeline

        if pipeline is None:
            pipeline = get_default_pipeline()

        self.prepare(request, progress_callback)

        def onfinish(client, errno, errmsg):
            self._cleanup()

            response = self.postmortem(request)

            finish_callback(response, errno, errmsg)

        pipeline.add(self, onfinish)
