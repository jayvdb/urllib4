#!/usr/bin/env python


import pycurl

class HttpResponse(object):
    BUILDIN_FIELDS = {
            'url': pycurl.EFFECTIVE_URL,
            'code': pycurl.RESPONSE_CODE,
            'connect_code': pycurl.HTTP_CONNECTCODE,
                
            # = Time = 
            #
            # An overview of the six time values available from curl_easy_getinfo()
            # 
            # curl_easy_perform()
            #     |
            #     |--NAMELOOKUP
            #     |--|--CONNECT
            #     |--|--|--APPCONNECT
            #     |--|--|--|--PRETRANSFER
            #     |--|--|--|--|--STARTTRANSFER
            #     |--|--|--|--|--|--TOTAL
            #     |--|--|--|--|--|--REDIRECT
                    
            'namelookup_time': pycurl.NAMELOOKUP_TIME,
            'connect_time': pycurl.CONNECT_TIME,
            #'appconnect_time': pycurl.APPCONNECT_TIME,
            'pretransfer_time': pycurl.PRETRANSFER_TIME,
            'starttransfer_time': pycurl.STARTTRANSFER_TIME,
            'total_time': pycurl.TOTAL_TIME,
            'redirect_time': pycurl.REDIRECT_TIME,
            
            'redirect_count': pycurl.REDIRECT_COUNT,
            'redirect_url': pycurl.REDIRECT_URL,
            
            'size_upload': pycurl.SIZE_UPLOAD,
            'size_download': pycurl.SIZE_DOWNLOAD,
            'speed_upload': pycurl.SPEED_UPLOAD,
            'speed_download': pycurl.SPEED_DOWNLOAD,
            'header_size': pycurl.HEADER_SIZE,
            'request_size': pycurl.REQUEST_SIZE,
            
            'ssl_verify_result': pycurl.SSL_VERIFYRESULT,
            'ssl_engines': pycurl.SSL_ENGINES,
            
            'content_length_upload': pycurl.CONTENT_LENGTH_UPLOAD,
            'content_length_download': pycurl.CONTENT_LENGTH_DOWNLOAD,
            'content_type': pycurl.CONTENT_TYPE,
            
            'os_errno': pycurl.OS_ERRNO,
            'num_connects': pycurl.NUM_CONNECTS,
            #'primary_ip': pycurl.PRIMARY_IP,
            
            'cookie_list': pycurl.COOKIELIST,
            'last_socket': pycurl.LASTSOCKET,
        }
            
    def __init__(self, client, request):
        self.client = client
        self.request = request
        
        self.cached_headers = None
        
    def __getattr__(self, name):

        if name in ['__iter__', 'next', 'isatty', 'seek', 'tell',
                    'read', 'readline', 'readlines', 'truncate',
                    'write', 'writelines', 'flush']:
            return getattr(self.client.body, name)
        elif self.BUILDIN_FIELDS.has_key(name):
            value = self.BUILDIN_FIELDS[name]
            
            if callable(value):
                return value()
            elif type(value) == tuple:
                field, convert = value
                
                return convert(self.client.curl.getinfo(field))
            else:
                return self.client.curl.getinfo(value)
            
        raise AttributeError(name)
    
    def close(self):
        pass
                
    def geturl(self):
        return self.url

    @property
    def headers(self):
        from httplib import HTTPMessage
        
        if not self.cached_headers:
            self.client.header.readline() # eat the first line 'HTTP/1.1 200 OK'
            self.cached_headers = HTTPMessage(self.client.header)
            self.client.header.seek(0)
            
        return self.cached_headers
    
    info = headers
        