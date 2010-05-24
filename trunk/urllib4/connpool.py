#!/usr/bin/env python
from __future__ import with_statement

import time
from datetime import datetime
import threading
import weakref

class FakeLock(object):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class BaseConnection(object):
    @property
    def connected(self):
        raise NotImplemented()
        
    def reconnect(self):
        raise NotImplemented()
        
    def reset(self):
        pass
        
    def __del__(self):
        self.reset()
        
        if hasattr(self, '_pool'):
            self._pool.put(self)

class ConnectionPool(object):
    WAIT_FOREVER = None
    WAIT_NERVER = 0
    
    def __init__(self, connection_creator, min_connections=0, max_connections=10,
                 multithreads=False):
        self.connection_creator = connection_creator
        self.min_connections = min_connections
        self.max_connections = max_connections
        
        self.lock = threading.Lock() if multithreads else FakeLock()
        self.idle_notify = threading.Event() if multithreads else None
        self.idle_conns = []
        self.used_conns = weakref.WeakKeyDictionary()
        
        if self.min_connections:            
            for i in range(self.min_connections):
                self.idle_conns.append(self.connection_creator())
            
    def __nonzero__(self):
        with self.lock:
            return (len(self.idle_conns) > 0) or (len(self.used_conns) < self.max_connections)
        
    def __len__(self):
        with self.lock:
            return len(self.idle_conns) + len(self.used_conns)
            
    def __repr__(self):
        return "<%s object (idle=%d, used=%d) at %08x>" % (type(self).__name__, len(self.idle_conns), len(self.used_conns), id(self))
        
    def get(self, timeout=WAIT_FOREVER):
        """
        get a connection from pool
        
        @param wait timeout for available connection (0 = nowait, None = forever)
        @return connection or None
        
        """
        while True:
            with self.lock:
                # try to get a connection from idle pool first                
                conn = self.idle_conns.pop(0) if self.idle_conns else None
                   
            if conn:
                # ensure the connection was connected or try to reconnect
                # if reconnect failed, drop the connection and try again
                
                try:
                    if conn.connected:
                        break
                    
                    if conn.reconnect():                    
                        break
                except AttributeError:
                    # ignore the connection instance doesn't support connected or reconnect
                    pass 
            else:
                # if no idle connection and not to many used, try to create one                
                if len(self.used_conns) < self.max_connections:
                    conn = self.connection_creator()
                    break
                
                # if too many used connections, return None for nowait 
                if timeout == ConnectionPool.WAIT_NERVER:
                    break
                
                # wait for idle connection, and try again without wait
                if self.idle_notify:
                    if timeout:
                        start_time = time.clock()
                    
                    self.idle_notify.wait(timeout)
                    
                    if timeout:
                        timeout = timeout - (time.clock() - start_time)
                        
                        if timeout < 0:
                            timeout = ConnectionPool.WAIT_NERVER
                    
                    continue
                else:
                    break
                    
        if conn:
            conn._pool = self
            
            if self.idle_notify:
                self.idle_notify.clear()
                
            # add connection to used pool for tracing
            with self.lock:
                self.used_conns[conn] = datetime.now()
        
        return conn
    
    def put(self, conn):
        with self.lock:
            if len(self.idle_conns) < self.min_connections:
                self.idle_conns.append(conn)
            
            if self.used_conns.has_key(conn):
                del self.used_conns[conn]
            
        if self.idle_notify:
            self.idle_notify.set()
 