#!/usr/bin/env python
from request import HttpRequest
from client import HttpClient
from flowcontrol import SiteProfile

Request = HttpRequest

def urlopen(url_or_request, data_or_reader=None, headers={}, method=None,
            guess_encoding=None, dnscache=None, pagecache=None,
            connect_callback=None, progress_callback=None,
            session_timeout=None, connect_timeout=None, *args, **kwds):

    if issubclass(type(url_or_request), HttpRequest):
        request = url_or_request
    else:
        request = HttpRequest(str(url_or_request), data_or_reader, headers, method, *args, **kwds)

    if session_timeout or connect_timeout:
        profile = SiteProfile.get(request.hostname)
        profile.timeout = session_timeout
        profile.connect_timeout = connect_timeout
    else:
        profile = None

    return HttpClient(dnscache=dnscache, pagecache=pagecache,
        profile=profile, guess_encoding=guess_encoding) \
            .perform(request, progress_callback, connect_callback)

def urlretrieve(url, filename=None, reporthook=None, data_or_reader=None,
                dnscache=None, pagecache=None, *args, **kwds):

    request = HttpRequest(url, data_or_reader, *args, **kwds)
    client = HttpClient(dnscache=dnscache, pagecache=pagecache)

    if filename:
        client.file = open(filename)
    else:
        fd, filename = mkstemp()
        client.file = os.fdopen(fd)

    def progress(download_total, downloaded, upload_total, uploaded):
        reporthook(downloaded, 1, download_total)

    response = client.perform(request, progress if reporthook else None)

    return (filename, response.headers)
