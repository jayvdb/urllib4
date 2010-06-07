#!/usr/bin/env python
import sys, re

RE_CONTENT_TYPE = re.compile('(?P<type>\w+/\w+);\s*charset=(?P<charset>[\w-]+)', re.I)

def guess_charset(header):
    if header is None:
        return None
    
    m = RE_CONTENT_TYPE.match(header)
    
    return m.group('charset') if m else None

def guess_encoding(content, suggest_encodings=[]):
    from BeautifulSoup import UnicodeDammit, BeautifulStoneSoup
    
    dammit = UnicodeDammit(content, isHTML=True,
                           overrideEncodings=suggest_encodings,
                           smartQuotesTo=BeautifulStoneSoup.HTML_ENTITIES)
    
    return dammit.unicode, dammit.originalEncoding, dammit.declaredHTMLEncoding

if __name__=='__main__':
    from client import HttpClient
    
    r = HttpClient(guess_encoding=['gbk', 'gb2312']).get(sys.argv[1])
     
    text = r.read().decode(r.encoding)
    
    print text