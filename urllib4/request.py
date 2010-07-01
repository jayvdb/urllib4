#!/usr/bin/env python
try:
    from gurl import Url
    urlparse = Url
except ImportError:
    from urlparse import urlparse

from urllib import unquote
from urlparse import urlunparse

import pycurl

REDIRECT_REFUSE     = 0
REDIRECT_INFINITE   = -1

def capitalize(key):
    return '-'.join([k.capitalize() for k in key.split('-')])

class HttpRequest(object):
    def __init__(self, url, data_or_reader=None, headers={}, method=None,
                 origin_req_host=None, unverifiable=False,
                 referer=None, user_agent=None,
                 session_timeout=None, connect_timeout=None,
                 interface=None, local_port=None, local_port_range=None, tcp_nodelay=None,
                 cookie_or_file=None, accept_encoding=None,
                 ssl_verify_peer=False, ssl_verify_host=False,
                 auto_referer=True, follow_location=True, max_redirects=REDIRECT_INFINITE,
                 http_version='last', realm=None, username=None, password=None, http_auth_mode=['any'],
                 proxy_host=None, proxy_type='http', proxy_auth_mode=['any']):

        u = urlparse(url)

        netloc = "%s:%d" % (u.hostname, u.port) if u.port else u.hostname
        params = u.params if hasattr(u, 'params') else ''

        self.url = urlunparse((u.scheme, netloc, u.path, params, u.query, u.fragment))
        self.data_or_reader = data_or_reader
        self.headers = {}
        self.headers.update(headers)
        self.method = method
        self.referer = referer
        self.user_agent = user_agent
        self.session_timeout = session_timeout
        self.connect_timeout = connect_timeout
        self.interface = interface
        self.local_port = local_port
        self.local_port_range = local_port_range
        self.tcp_nodelay = tcp_nodelay
        self.cookie_or_file = cookie_or_file
        self.accept_encoding = accept_encoding
        self.ssl_verify_peer = ssl_verify_peer
        self.ssl_verify_host = ssl_verify_host
        self.auto_referer = auto_referer
        self.follow_location = follow_location
        self.max_redirects = max_redirects
        self.set_http_version(http_version)
        self.realm = realm
        self.username = username or unquote(u.username or '')
        self.password = password or unquote(u.password or '')
        self.http_auth_mode = self._convert_auth_mode(http_auth_mode)
        self.set_proxy(proxy_host, proxy_type, proxy_auth_mode)

    def _convert_auth_mode(self, modes):
        AUTH_MODES = {
            'basic': pycurl.HTTPAUTH_BASIC,             # HTTP Basic authentication.
            'digest': pycurl.HTTPAUTH_DIGEST,           # HTTP Digest authentication.
            'negotiate': pycurl.HTTPAUTH_GSSNEGOTIATE,  # HTTP GSS-Negotiate authentication.
            'ntlm': pycurl.HTTPAUTH_NTLM,               # HTTP NTLM authentication.
            'any': pycurl.HTTPAUTH_ANY,
            'anysafe': pycurl.HTTPAUTH_ANYSAFE,
            'none': pycurl.HTTPAUTH_NONE,
        }

        if not issubclass(type(modes), list):
            modes = [modes]

        auth_mode = 0

        for mode in modes:
            auth_mode |= AUTH_MODES.get(mode.lower(), 0)

        return auth_mode

    def hostname(self):
        return urlparse(self.url).hostname

    def get_method(self):
        '''Return a string indicating the HTTP request method. '''
        return self.method or ('POST' if self.has_data() else 'GET')

    def add_data(self, data):
        '''Set the Request data to data.'''
        self.data_or_reader = data

    def has_data(self):
        '''Return whether the instance has a non-None data.'''
        return self.data_or_reader is not None

    def get_data(self):
        '''Return the instance's data. '''
        return self.data_or_reader

    def add_header(self, key, val):
        '''Add another header to the request.'''
        self.headers[capitalize(key)] = val

    def has_header(self, header):
        '''Return whether the instance has the named header.'''
        return self.headers.has_key(header)

    def get_full_url(self):
        '''Return the URL given in the constructor.'''
        return self.url

    def get_type(self):
        '''Return the type of the URL -- also known as the scheme. '''
        return urlparse(self.url).scheme

    def get_host(self):
        '''Return the host to which a connection will be made.'''
        return urlparse(self.url).hostname

    def get_selector(self):
        '''Return the selector -- the part of the URL that is sent to the server.'''
        return urlparse(self.url).path

    def set_proxy(self, host, type='http', auth_mode='basic'):
        '''
        Prepare the request by connecting to a proxy server.
        The host and type will replace those of the instance,
        and the instance's selector will be the original URL given in the constructor.
        '''
        PROXY_TYPES = {
            'http': pycurl.PROXYTYPE_HTTP,
            'sock4': pycurl.PROXYTYPE_SOCKS4,
            'sock5': pycurl.PROXYTYPE_SOCKS5,
        }

        self.proxy_auth = None

        try:
            o = urlparse(host)

            if o and o.netloc:
                host = o.netloc
                type = o.scheme
                self.proxy_auth = '%s:%s' % (o.username, o.password)
        except:
            pass

        self.proxy_host = host
        self.proxy_type = PROXY_TYPES.get(type.lower(), pycurl.PROXYTYPE_HTTP)
        self.proxy_auth_mode = self._convert_auth_mode(auth_mode)

    def set_http_version(self, version):
        HTTP_VERSIONS = {
            '1.0': pycurl.CURL_HTTP_VERSION_1_0,
            '1.1': pycurl.CURL_HTTP_VERSION_1_1,
            'last': pycurl.CURL_HTTP_VERSION_LAST,
            'none': pycurl.CURL_HTTP_VERSION_NONE,
        }

        self.http_version = HTTP_VERSIONS.get(version.lower(), pycurl.CURL_HTTP_VERSION_LAST)
