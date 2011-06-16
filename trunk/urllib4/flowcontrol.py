#!/usr/bin/env python
from __future__ import with_statement

import time
import threading

import pycurl

def synchronized(func):
    def wrap(self, *args, **kwds):
        if not hasattr(self, '__lock'):
            self.__lock = threading.RLock()

        self.__lock.acquire()
        try:
            return func(self, *args, **kwds)
        finally:
            self.__lock.release()
        
    return wrap

class TokenBucket(object):
    """An implementation of the token bucket algorithm.
    
      wiki: http://en.wikipedia.org/wiki/Token_bucket
    source: http://code.activestate.com/recipes/511490/

    >>> bucket = TokenBucket(80, 0.5)
    >>> print bucket.consume(10)
    True
    >>> print bucket.consume(90)
    False
    """
    def __init__(self, tokens, fill_rate):
        """
        @param tokens: the total tokens in the bucket.
        @param fill_rate: the rate in tokens/second that the bucket will be refilled.
        """
        assert type(tokens) in (int,float,long)
        assert type(fill_rate) in (int,float,long) and fill_rate > 0.0

        self.capacity = float(tokens)
        self._tokens = float(tokens)
        self.fill_rate = float(fill_rate)

        self.timestamp = time.time()

    def update(self, tokens):
        return self._tokens

    @synchronized
    def consume(self, tokens):
        """
        Consume tokens from the bucket.

        Returns 0 if there were sufficient tokens,
        otherwise the expected time until enough tokens become available.
        """
        expected_time = round((tokens - self.tokens) / self.fill_rate)
        if expected_time <= 0:
            self._tokens -= tokens
        return max(0, expected_time)

    @property
    @synchronized
    def tokens(self):
        if self._tokens < self.capacity:
            now = time.time()
            delta = round(self.fill_rate * (now - self.timestamp))
            self._tokens = min(self.capacity, self._tokens + delta)
            self.timestamp = now
            
        return self._tokens

class LeakyBucket(object):
    """An implementation of the token bucket algorithm.

      wiki: http://en.wikipedia.org/wiki/Leaky_bucket
    source: http://www.koders.com/python/fid8AD71F071B1B61FBFA177F64F4D48E84F76DB620.aspx?s=fuzzy
    """
    def __init__(self, interval, max_rate, burst_rate=2.0):
        """
        @param interval: the time between rate adjustments.
        @param max_rate: the maxiume rate in tokens/second that the bucket will be refilled.
        """
        assert type(interval) in (int,float,long) and interval > 0.0
        assert type(max_rate) in (int, float, long) and max_rate > 0.0

        self.interval = float(interval)
        self.max_rate = float(max_rate)

        self._tokens = 0.0 # number of bytes that can be sent.
        self._max_tokens = burst_rate * max_rate * interval # ensures enough for continuous transmission except for really bursty sources.

        self.timestamp = time.time()

    @synchronized
    def update(self, tokens):
        self._tokens = max(0, self.tokens - tokens)

        return self._tokens

    @synchronized
    def consume(self, tokens):
        """
        Consume tokens from the bucket.

        Returns 0 if there were sufficient tokens,
        otherwise the expected time until enough tokens become available.
        """
        expected_time = round((self.tokens + tokens - self._max_tokens) / (self.max_rate * self.interval))

        if expected_time <= 0:
            self._tokens += tokens

        return max(0, expected_time)

    @property
    @synchronized
    def tokens(self):
        if self._tokens > 0:
            now = time.time()
            delta = round(self.max_rate * (now - self.timestamp) / self.interval)
            self._tokens = max(0, self._tokens - delta)
            self.timestamp = now

        return self._tokens

class RateLimit(object):
    """Rate limit a url fetch.
    
    source: http://mail.python.org/pipermail/python-list/2008-January/472859.html
    """
    def __init__(self, bucket, filename):
        self.bucket = bucket
        self.last_update = 0
        self.last_downloaded_kb = 0

        self.filename = filename
        self.avg_rate = None

    def __call__(self, block_count, block_size, total_size):
        total_kb = total_size / 1024.

        downloaded_kb = (block_count * block_size) / 1024.
        just_downloaded = downloaded_kb - self.last_downloaded_kb
        self.last_downloaded_kb = downloaded_kb

        predicted_size = block_size/1024.

        wait_time = self.bucket.consume(predicted_size)
        while wait_time > 0:
            time.sleep(wait_time)
            wait_time = self.bucket.consume(predicted_size)

        now = time.time()
        delta = now - self.last_update
        if self.last_update != 0:
            if delta > 0:
                rate = just_downloaded / delta
                if self.avg_rate is not None:
                    rate = 0.9 * self.avg_rate + 0.1 * rate
                self.avg_rate = rate
            else:
                rate = self.avg_rate or 0.
            print "%20s: %4.1f%%, %5.1f KiB/s, %.1f/%.1f KiB" % (
                    self.filename, 100. * downloaded_kb / total_kb,
                    rate, downloaded_kb, total_kb,
                )
        self.last_update = now

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

import unittest

class BucketTestCase(unittest.TestCase):
    def testTokenBucket(self):
        tb = TokenBucket(100, 10)

        self.assertEquals(100, tb.tokens)

        self.assertEquals(0, tb.consume(40))

        self.assertEquals(60, tb.tokens)

        self.assertEquals(0, tb.consume(40))

        self.assertEquals(20, tb.tokens)

        self.assertEquals(2, tb.consume(40))

        tb.timestamp -= 1

        self.assertEquals(30, tb.tokens)

        self.assertEquals(1, tb.consume(40))

        tb.timestamp -= 1

        self.assertEquals(40, tb.tokens)

        self.assertEquals(0, tb.consume(35))

        self.assertEquals(5, tb.tokens)

    def testLeakyBucket(self):
        lb = LeakyBucket(1, 10)

        self.assertEquals(0, lb.tokens)

        self.assertEquals(0, lb.consume(10))

        self.assertEquals(10, lb.tokens)

        self.assertEquals(0, lb.consume(10))

        self.assertEquals(20, lb.tokens)

        self.assertEquals(2, lb.consume(20))

        lb.timestamp -= 1

        self.assertEquals(10, lb.tokens)

        self.assertEquals(1, lb.consume(20))

        lb.timestamp -= 1

        self.assertEquals(0, lb.tokens)

        self.assertEquals(0, lb.consume(15))

        self.assertEquals(15, lb.tokens)

if __name__ == '__main__':
    unittest.main()