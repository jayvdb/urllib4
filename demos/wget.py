#!/usr/bin/env python
from __future__ import with_statement

import sys, os, os.path
from datetime import datetime
import logging

try:
    from gurl import Url as urlparse
except ImportError:
    from urlparse import urlparse

import urllib4

DEFAULT_LOG_LEVEL = logging.WARN
DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s [%(process)d:%(thread)d] %(module)s.%(name)s: %(message)s'

def parse_cmdline():
    from optparse import OptionParser
    
    parser = OptionParser("Usage: %prog [options] <url> ...")
    
    parser.add_option('-v', '--verbose', action='store_const',
                      const=logging.INFO, dest='log_level', default=DEFAULT_LOG_LEVEL,
                      help='Show the verbose information')
    parser.add_option('-d', '--debug', action='store_const',
                      const=logging.DEBUG, dest='log_level',
                      help='Show the debug information')    
    parser.add_option('--log-format', dest='log_format',
                      metavar='FMT', default=DEFAULT_LOG_FORMAT,
                      help='Format to output the log')
    parser.add_option('--log-file', dest='log_file', metavar='FILE',
                      help='File to write log to. Default is `stdout`.')
    
    opts, args = parser.parse_args()

    logging.basicConfig(level=opts.log_level,
                        format=opts.log_format,
                        filename=opts.log_file,
                        stream=sys.stdout)
    
    return opts, args

def size_pretty(size):
    KB = 1024
    MB = KB * 1024
    GB = MB * 1024
    
    if size > GB:
        return "%.1fG" % (size / GB)
    if size > MB:
        return "%.1fM" % (size / MB)
    if size > KB:
        return "%.1fK" % (size / KB)
    
    return "%dB" % int(size)

if __name__ == '__main__':
    opts, args = parse_cmdline()

    c = urllib4.HttpClient();
    
    for url in args:
        print "--%s-- %s" % (datetime.now(), url)
        
        o = urlparse(url)
        
        filename = os.path.basename(o.path)
        
        print "HTTP request sent, awaiting response...",
        
        download_progress = []
                
        def onprogress(download_total, downloaded, upload_total, uploaded):
            if len(download_progress) == 0:
                print c.status
                print "Length: %d (%s) [%s]" % (int(download_total), size_pretty(download_total), c.headers.get('Content-Type'))
                
                print "Saving to: `%s`" % filename
                
            download_progress.append([datetime.now(), downloaded])
                
            return urllib4.PROGRESS_CALLBACK_CONTINUE
                    
        with open(filename, 'wb') as f:
            c.download(url, f, progress_callback=onprogress)