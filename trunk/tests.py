#!/usr/bin/env python
from urllib4 import *

import unittest

class TestUrlLib(unittest.TestCase):
    def testOpen(self):
        url = 'http://code.google.com/p/urllib4/'
        
        r = urlopen(url)
        
        self.assert_(url, r.geturl())
        self.assertEquals(200, r.code)
        self.assert_(len(r.read()) > 100)        
        
        self.assert_(r.headers)
        self.assert_(r.headers.has_key('content-type'))
        
class TestRequst(unittest.TestCase):
    def testHeader(self):
        request = HttpRequest('http://code.google.com/p/urllib4/',
                              referer='http://www.google.com',
                              user_agent='urllib4',
                              cookie_or_file='sender=urllib4',
                              accept_encoding='en')
        
        response = HttpClient().perform(request)
        
    def testCallback(self):
        result = {}
        
        request = HttpRequest('http://code.google.com/p/urllib4/')
            
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
        
if __name__=='__main__':    
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARN,
                        format='%(asctime)s %(levelname)s %(message)s')
    
    unittest.main()