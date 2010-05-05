#!/usr/bin/env python
from __future__ import with_statement

import threading

import socket 

class DnsCache(object):
    def __init__(self):
        self.cache = {}
        self.cache_lock = threading.Lock()
    
    def get(self, domain):
        with self.cache_lock:
            addresses = self.cache.get(domain)
            
        if not addresses: 
            addresses = self.query(domain)
                
            with self.cache_lock:
                self.cache[domain] = addresses
                
        return addresses
    
    def query(self, domain):
        #TODO return a wrapped async DNS record
        return [socket.gethostbyname(domain)]