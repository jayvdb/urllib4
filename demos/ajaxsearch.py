#!/usr/bin/env python
import sys
import locale
import logging

try:
    import json
except ImportError:
    import simplejson as json

from urllib import urlencode

from urllib4 import urlopen

SYSTEM_LANGUAGE = locale.getdefaultlocale()[0]
DEFAULT_LANGUAGE = 'en'
DEFAULT_COUNTRY = 'us'

DEFAULT_LOG_LEVEL = logging.WARN
DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s [%(process)d:%(thread)d] %(module)s.%(name)s: %(message)s'

CHROME_USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.1 (KHTML, like Gecko) Chrome/6.0.422.0 Safari/534.1'

#
# This optional argument supplies the search safety level which may be one of:
#
SAFE_ACTIVE = 'active'      # enables the highest level of safe search filtering
SAFE_MODERATE = 'moderate'  # enables moderate safe search filtering (default)
SAFE_OFF = 'off'            # disables safe search filtering
SAFE_DEFAULT = SAFE_MODERATE

class GoogleQueryResult(object):
    def __init__(self, result):
        self.result = result
        
    def __getattr__(self, name):
        if self.result.has_key(name):
            return self.result[name]
            
        raise AttributeError("Attribute %s not found." % name)        

class GoogleAjaxQuery(object):
    SEARCH_PATH = 'https://ajax.googleapis.com/ajax/services/search/web'

    def __init__(self, params, count):
        self.params = params
        self.count = count
        
    def __iter__(self):
        while self.params['start'] < self.count:
            url = self.SEARCH_PATH + '?' + urlencode(self.params)
            
            response = json.loads(urlopen(url, user_agent=CHROME_USER_AGENT).read())
            
            if response['responseStatus'] == 200:
                results = response['responseData']['results']
                
                for result in results:
                    self.params['start'] += 1
                    
                    if self.params['start'] >= self.count:
                        break
                    
                    yield GoogleQueryResult(result)

class GoogleAjaxSearcher(object):
    def __init__(self, language=DEFAULT_LANGUAGE,
                 lang_filter=None, country=DEFAULT_COUNTRY,
                 safe=SAFE_DEFAULT, duplicate_filter=True):
        self.language = language
        self.lang_filter = lang_filter
        self.country = country
        self.safe = safe
        self.duplicate_filter = duplicate_filter
        
    def query(self, keywords, start=0, count=10):
        params = {
            'q': '+'.join(keywords),
            'v': '1.0',
            'start': start,
        }
        
        if self.language != DEFAULT_LANGUAGE:
            params['hr'] = self.language

        if self.lang_filter:
            params['lr'] = self.lang_filter
            
        if self.country != DEFAULT_COUNTRY:
            params['gl'] = self.country
                
        if self.safe != SAFE_DEFAULT:
            params['safe'] = self.safe
            
        if not self.duplicate_filter:
            params['filter'] = 0
            
        return GoogleAjaxQuery(params, count)

def parse_cmdline():
    from optparse import OptionParser
    
    parser = OptionParser("Usage: %prog [options] <keyword> ...")
    
    parser.add_option('-c', '--count', default=10,
                      help='Set the search result count (default is 10)')
    parser.add_option('-l', '--language', dest='language', default=SYSTEM_LANGUAGE,
                      help='Set the search language (default is %s)' % SYSTEM_LANGUAGE)
    parser.add_option('--language-filter', dest='lang_filter', default=None,
                      help='restrict the search to documents written in a particular language')
    parser.add_option('--country', default=DEFAULT_COUNTRY,
                      help='tailor the results to a specific country')
    
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

if __name__=='__main__':
    opts, args = parse_cmdline()
    
    searcher = GoogleAjaxSearcher(opts.language, opts.lang_filter, opts.country)
    
    args = [arg.decode(sys.getfilesystemencoding()).encode('utf-8') for arg in args]
    
    for result in searcher.query(args, count=opts.count):
        print result.url