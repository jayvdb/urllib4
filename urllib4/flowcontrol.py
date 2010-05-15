#!/usr/bin/env python
import threading

import pycurl

class SiteProfile(object):
    FIELDS = {
        'timeout': pycurl.TIMEOUT,
        'timeout_ms': pycurl.TIMEOUT_MS,
        'connect_timeout': pycurl.CONNECTTIMEOUT,
        'connect_timeout_ms': pycurl.CONNECTTIMEOUT_MS,
        
        'low_speed_limit': pycurl.LOW_SPEED_LIMIT,
        'low_speed_time': pycurl.LOW_SPEED_TIME,
        'max_send_speed_large': pycurl.MAX_SEND_SPEED_LARGE,
        'max_recv_speed_large': pycurl.MAX_RECV_SPEED_LARGE,
        
        'max_connects': pycurl.MAXCONNECTS,
        'fresh_connect': pycurl.FRESH_CONNECT,
        'forbid_reuse': pycurl.FORBID_REUSE,
    }
    
    def __init__(self, domain, *args, **kwds):
        self.domain = domain
        
        for name in SiteProfile.FIELDS.keys():
            setattr(self, name, None)
        
        for name, value in kwds.items():
            if not hasattr(self, name):
                raise NameError("name '%s' is not defined" % name)
                
            setattr(self, name, value)
           
    profilers = {}
    profiler_lock = threading.Lock()
           
    @staticmethod 
    def get(domain, *args, **kwds):
        with SiteProfile.profiler_lock:
            return SiteProfile.profilers.setdefault(domain, SiteProfile(domain, *args, **kwds))
            
    def apply(self, curl):
        for name, key in SiteProfile.FIELDS.items():
            value = getattr(self, name)
            
            if value:
                curl.setopt(key, value)