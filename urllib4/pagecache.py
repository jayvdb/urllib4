#!/usr/bin/env python
import memcache

try:
    import json
except ImportError:
    import simplejson as json

class BasePage(object):
    def __init__(self, cache, key, md5=None, etag=None, last_modified=None):
        self.cache = cache
        self.key = key
        self.md5 = md5
        self.etag = etag
        self.last_modified = last_modified

    def update(self):
        self.cache.update(self)

    def __repr__(self):
        return "<%s key=%s, md5=%s, etag=%s, last_modified=%s>" % \
            (self.__class__.__name__, self.key, self.md5, self.etag, self.last_modified)

class BasePageCache(object):
    def key(self, method, url):
        return "%s:%s" % (method, url)

    def get(self, url, method):
        raise NotImplementedError()

    def update(self, page):
        raise NotImplementedError()

class DictPageCache(BasePageCache):
    def __init__(self):
        BasePageCache.__init__(self)

        self.pages = {}

    def get(self, url, method):
        key = self.key(method, url)

        return self.pages.setdefault(key, BasePage(self, key))

    def update(self, page):
        pass

class MemcachePageCache(BasePageCache):
    def __init__(self, servers, debug=False):
        BasePageCache.__init__(self)

        self.mc = memcache.Client(servers, debug=1 if debug else 0)

    def get(self, url, method):
        key = self.key(method, url)
        data = self.mc.get(key)

        params = dict([(k.encode('utf-8'), v.encode('utf-8') if v else v) for k, v in json.loads(data).items()])

        page = BasePage(self, key, **params) if data else BasePage(self, key)

        return page

    def update(self, page):
        self.mc.set(page.key, json.dumps({
            'md5': page.md5,
            'etag': page.etag,
            'last_modified': page.last_modified,
        }))
