#!/usr/bin/env python
from __future__ import with_statement

import threading
from Queue import Queue

import pycurl

class Dispatcher(object):
    def __init__(self, concurrency=2):
        self.workers = [threading.Thread(target=self.work, name="dispatcher") for i in range(concurrency)]

        for worker in self.workers:
            worker.setDaemon(True)
            worker.start()

        self.terminated = False
        self.tasks = Queue()

    def terminate(self):
        self.terminated = True

    def dispatch(self, callback, *args, **kwds):
        if len(self.workers) > 0:
            self.tasks.put((callback, args, kwds))
        else:
            try:
                callback(*args, **kwds)
            except:
                import traceback

                traceback.print_exc()

    def work(self):
        while True:
            callback, args, kwds = self.tasks.get()

            try:
                callback(*args, **kwds)
            except:
                import traceback

                traceback.print_exc()

            self.tasks.task_done()

class HttpPipeline(threading.Thread):
    def __init__(self, dispatcher=None, concurrency=None, loop_interval=1.0):
        threading.Thread.__init__(self, name="pipeline")

        self.setDaemon(True)

        self.dispatcher = dispatcher

        if self.dispatcher is None:
            if concurrency is None:
                self.dispatcher = Dispatcher()
            else:
                self.dispatcher = Dispatcher(concurrency)

        self.loop_interval = loop_interval
        self.pipeline = pycurl.CurlMulti()
        self.clients = {}
        self.lock = threading.RLock()

        self.terminated = False

    def close(self):
        self.pipeline.close()

    def terminate(self):
        self.terminated = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def add(self, client, callback):
        with self.lock:
            self.clients[client.curl] = (client, callback)

            self.pipeline.add_handle(client.curl)

            return client

    def remove(self, client):
        with self.lock:
            client, callback = self.clients[client.curl]

            del self.clients[client.curl]

            self.pipeline.remove_handle(client.curl)

            return client, callback

    def run(self):
        while not self.terminated:
            while not self.terminated:
                ret, num_handles = self.pipeline.perform()

                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

            if self.terminated:
                break

            while not self.terminated:
                num_queued, ok_list, err_list = self.pipeline.info_read()

                for curl in ok_list:
                    with self.lock:
                        client, callback = self.remove(self.clients[curl])

                    self.dispatcher.dispatch(callback, client, 0, None)

                for curl, errno, errmsg in err_list:
                    with self.lock:
                        client, callback = self.remove(self.clients[curl])

                    self.dispatcher.dispatch(callback, client, errno, errmsg)

                if num_queued == 0:
                    break

            self.pipeline.select(self.loop_interval)

__pipeline = None

def get_default_pipeline():
    if __pipeline is None:
        __pipeline = HttpPipeline()
        __pipeline.start()

    return __pipeline
