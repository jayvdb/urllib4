#!/usr/bin/env python
from __future__ import with_statement

import sys
import os, os.path
import time
from hashlib import md5
import socket
import logging

try:
    import simplejson as json
except ImportError:
    import json 

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from OpenSSL import SSL

import urllib, cgi
import pycurl

import unittest

from urllib4 import *

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
        elif self.path == '/slow':
            time.sleep(5)
            return self.response("finished")
        else:
            headers = {
                'path': self.path
            }
            headers.update(self.headers.items())
            
            return self.response(json.dumps(headers))
        
    def do_POST(self):
        length = int(self.headers.getheader('content-length'))
        
        result = cgi.parse_qs(self.rfile.read(length))
        result.update(self.headers.items())        
        
        return self.response(json.dumps(result))
        
    def do_TEST(self):
        return self.response('test')
        
class TestHTTPServer(HTTPServer):
    def __init__(self, port=80, host='localhost', handler=TestHTTPRequestHandler):
        HTTPServer.__init__(self, (host, port), handler)
        
        self._port=port
        self._host=host
        
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
        return self._host
        
    @property
    def port(self):
        return self._port
    
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
    def __init__(self, port=443, host='localhost', handler=TestSecureHTTPRequestHandler):
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
    def testGet(self):
        with TestHTTPServer() as httpd:
            r = urlopen(httpd.root)
            
            self.assert_(httpd.root, r.geturl())
            self.assertEquals(200, r.code)
            self.assert_(len(r.read()) > 10)        
            
            self.assert_(r.headers)
            self.assert_(r.headers.has_key('content-type'))
            
    def testPost(self):
        with TestHTTPServer() as httpd:
            r = urlopen(httpd.root, {'key': 'value'})
            
            self.assert_(httpd.root, r.geturl())
            self.assertEquals(200, r.code)
            
            params = json.loads(r.read())
            
            self.assertEquals([u'value'], params['key'])
            
            r = urlopen(httpd.root, 'key=value')

            params = json.loads(r.read())
            
            self.assertEquals([u'value'], params['key'])
            
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
            
    def testHeader(self):
        with TestHTTPServer() as httpd:
            request = HttpRequest(httpd.root + 'post', headers={'key': 'value'})
            request.has_header('key')
            request.add_header('name', 'value')
            request.has_header('name')
            
            response = HttpClient().perform(request)
            
            result = json.loads(response.read())
            
            self.assertEqual('value', result['key'])
            self.assertEqual('value', result['name'])
            
    def testProxy(self):
        with TestHTTPServer() as httpd:
            request = HttpRequest(httpd.root)
            request.set_proxy('http://user:pass@127.0.0.1:80')
            
            response = HttpClient().perform(request)
            
            result = json.loads(response.read())
            
            self.assertEqual(httpd.root, result['path'])
            self.assertEqual("Basic dXNlcjpwYXNz", result['proxy-authorization'])
            
    def testCustomRequest(self):
        with TestHTTPServer() as httpd:
            request = HttpRequest(httpd.root, http_custom_request='TEST')
            response = HttpClient().perform(request)
            self.assertEqual("test", response.read())
            
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
            self.assertEqual('127.0.0.1', response.primary_ip)
            
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
            except TooManyRedirects, e:
                self.assertEquals(pycurl.E_TOO_MANY_REDIRECTS, e.code)
                
            try:
                HttpClient().perform(HttpRequest(httpd.root + 'redirect/2', max_redirects=1))
                self.fail()
            except TooManyRedirects, e:
                self.assertEquals(pycurl.E_TOO_MANY_REDIRECTS, e.code)
                
            r = HttpClient().perform(HttpRequest(httpd.root + 'redirect/2', max_redirects=2))
            
            self.assert_(url, r.geturl())
            self.assertEquals(200, r.code)
            self.assert_(len(r.read()) > 10)
            
class TestClient(unittest.TestCase):
    def testDestructor(self):
        import gc
        
        with TestHTTPServer() as httpd:
            HttpClient().get(httpd.root + 'host')
            
            gc.collect()
            
            self.assertFalse(gc.garbage)
            
class TestDnsCache(unittest.TestCase):
    def testCache(self):
        c = DnsCache()
        
        self.assertEquals({}, c.cache)
        
        self.assertEqual(['127.0.0.1'], c.get('localhost'))
        self.assertEqual(['127.0.0.1'], c.cache['localhost'])
        
    def testHost(self):
        c = DnsCache()
        
        self.assertEquals({}, c.cache)
        
        with TestHTTPServer() as httpd:
            response = HttpClient(dnscache=c).get(httpd.root + 'host')
            
            self.assertEquals(200, response.code)
            
        result = json.loads(response.read())
            
        self.assertEqual(['127.0.0.1'], c.cache['localhost'])
        self.assertEqual('localhost', result['host'])
        
class TestFlowControl(unittest.TestCase):
    def testTimeout(self):
        profile = SiteProfile.get('test', timeout_ms=1000)
        
        self.assertEqual(None, profile.timeout)
        self.assertEqual(1000, profile.timeout_ms)
        
        cache = DnsCache()
        cache.set('test', ['127.0.0.1'])
        
        with TestHTTPServer() as httpd:        
            ts = time.clock()
                    
            try:
                HttpClient(dnscache=cache, profile=profile).get('http://test/slow')
                
                self.fail()
            except OperationTimeoutError:
                pass
            
            self.assert_(time.clock() - ts < 5)
            
            SiteProfile.get('test').timeout = 10
            
            r = HttpClient(dnscache=cache).get('http://test/slow')
            
            self.assertEqual('finished', r.read())
            
if __name__=='__main__':    
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARN,
                        format='%(asctime)s %(levelname)s %(message)s')
    
    unittest.main()