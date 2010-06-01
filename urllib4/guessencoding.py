#!/usr/bin/env python
import re

RE_CONTENT_TYPE = re.compile('(?P<type>\w+/\w+);\s+charset=(?P<charset>[\w-]+)', re.I)

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