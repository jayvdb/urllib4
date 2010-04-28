#!/usr/bin/env python
from __future__ import with_statement

import sys
import os, os.path
from hashlib import md5
import socket

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from OpenSSL import SSL

from urllib4 import *

import unittest

class TestHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info(format, *args)

    def response(self, data, mimetype='text/html'):
        self.send_response(200)
        self.send_header("Content-type", mimetype)
        self.send_header("Content-Length", len(data))
        self.send_header("ETag", md5(data).hexdigest())
        self.end_headers()
        
        self.wfile.write(data)
        
    def redirect(self, path):
        self.send_response(301)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        if self.path == '/':
            return self.response("<html><body>Hello World</body></html>")
        elif self.path == '/redirect':
            return self.redirect('/')
        elif self.path == '/redirect/2':
            return self.redirect('/redirect')
        else:
            return self.response(self.path)
        
class TestHTTPServer(HTTPServer):
    def __init__(self, port=80, host='127.0.0.1', handler=TestHTTPRequestHandler):
        HTTPServer.__init__(self, (host, port), handler)
        
    def run(self):
        try:
            self.serve_forever()
        except:
            pass
                
    def __enter__(self):
        from threading import Thread
        
        self.t = Thread(target=self.run)
        self.t.setDaemon(True)
        self.t.start()
        
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.server_close()
    
    @property    
    def scheme(self):
        return 'http'
    
    @property
    def host(self):
        return self.socket.getsockname()[0]
        
    @property
    def port(self):
        return self.socket.getsockname()[1]
    
    @property
    def root(self):
        return '%s://%s:%d/' % (self.scheme, self.host, self.port)
            
#
# Simple HTTP server supporting SSL secure communications
#
# http://code.activestate.com/recipes/442473-simple-http-server-supporting-ssl-secure-communica/
#
class TestSecureHTTPRequestHandler(TestHTTPRequestHandler):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

class TestSecureHTTPServer(TestHTTPServer):
    def __init__(self, port=443, host='127.0.0.1', handler=TestSecureHTTPRequestHandler):
        TestHTTPServer.__init__(self, port, host, handler)
        
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey_file('server.pem')
        ctx.use_certificate_file('server.pem')
        
        self.socket = SSL.Connection(ctx, socket.socket(self.address_family, self.socket_type))
        self.server_bind()
        self.server_activate()

    @property    
    def scheme(self):
        return 'https'

class TestUrlLib(unittest.TestCase):
    def testOpen(self):
        with TestHTTPServer() as httpd:
            r = urlopen(httpd.root)
            
            self.assert_(httpd.root, r.geturl())
            self.assertEquals(200, r.code)
            self.assert_(len(r.read()) > 10)        
            
            self.assert_(r.headers)
            self.assert_(r.headers.has_key('content-type'))
            
    def testSecure(self):
        with TestSecureHTTPServer() as httpd:
            r = urlopen(httpd.root)
            
            self.assert_(httpd.root, r.geturl())
            self.assertEquals(200, r.code)
            self.assert_(len(r.read()) > 10)        
            
            self.assert_(r.headers)
            self.assert_(r.headers.has_key('content-type'))
        
class TestRequst(unittest.TestCase):
    def testHeader(self):
        with TestHTTPServer() as httpd:
            request = HttpRequest(httpd.root,
                                  referer='http://www.google.com',
                                  user_agent='urllib4',
                                  cookie_or_file='sender=urllib4',
                                  accept_encoding='en')
            
            response = HttpClient().perform(request)
        
    def testCallback(self):
        with TestHTTPServer() as httpd:
            result = {}
            
            request = HttpRequest(httpd.root)
                
            response = HttpClient().perform(request,
                progress_callback=lambda download_total, downloaded, upload_total, uploaded:
                    result.update({
                        'download_total': download_total,
                        'downloaded': downloaded,
                        'upload_total': upload_total,
                        'uploaded': uploaded}))        
            
            self.assert_(result.has_key('download_total'))
            self.assert_(result.has_key('downloaded'))
            self.assert_(result.has_key('upload_total'))
            self.assert_(result.has_key('uploaded'))
            
            
    def testProxy(self):
        with TestHTTPServer() as httpd:            
            request = HttpRequest(httpd.root)
            request.set_proxy('127.0.0.1:80')
            
            response = HttpClient().perform(request)
            
            self.assertEqual(httpd.root, response.read())
            
class TestResponse(unittest.TestCase):
    def testInfo(self):
        with TestHTTPServer() as httpd:
            response = HttpClient().get(httpd.root)
            
            self.assert_(response.namelookup_time >= 0)
            self.assert_(response.connect_time >= 0)
            #self.assert_(response.appconnect_time > 0)
            self.assert_(response.pretransfer_time >= 0)
            self.assert_(response.starttransfer_time >= 0)
            self.assert_(response.total_time >= 0)
            self.assert_(response.redirect_time >= 0)
            
    def testRedirect(self):
        with TestHTTPServer() as httpd:
            url = httpd.root + 'redirect'
            r = HttpClient().get(url)
            
            self.assert_(httpd.root, r.geturl())
            self.assertEquals(200, r.code)
            self.assert_(len(r.read()) > 10)
            
            self.assertEqual(1, r.redirect_count)
            self.assertEqual(None, r.redirect_url)
            
            r = HttpClient().perform(HttpRequest(url, follow_location=False))

            self.assert_(url, r.geturl())
            self.assertEquals(301, r.code)
            self.assert_(len(r.read()) == 0)
            
            self.assertEqual(0, r.redirect_count)
            self.assertEqual(httpd.root, r.redirect_url)
            
            try:
                HttpClient().perform(HttpRequest(url, max_redirects=0))
                self.fail()
            except Exception, (code, msg):
                self.assertEquals(pycurl.E_TOO_MANY_REDIRECTS, code)
                
            try:
                HttpClient().perform(HttpRequest(httpd.root + 'redirect/2', max_redirects=1))
                self.fail()
            except Exception, (code, msg):
                self.assertEquals(pycurl.E_TOO_MANY_REDIRECTS, code)
                
            r = HttpClient().perform(HttpRequest(httpd.root + 'redirect/2', max_redirects=2))
            
            self.assert_(url, r.geturl())
            self.assertEquals(200, r.code)
            self.assert_(len(r.read()) > 10)
            
if __name__=='__main__':    
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARN,
                        format='%(asctime)s %(levelname)s %(message)s')
    
    unittest.main()