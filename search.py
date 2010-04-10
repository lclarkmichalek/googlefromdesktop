#!/bin/python
# -*- coding: utf-8 -*-
import urllib2, simplejson, socket, re, optparse, sys
from sys import argv, exit
from optparse import OptionParser

parser = OptionParser(usage='%prog [-c COLOR] [-s, --screenshot]',)
parser.add_option('-s', '--search',
    action='store_true', dest='search', help='just search')
(options, args) = parser.parse_args()

if options.search != None:
    SEARCH = True
else: SEARCH = False


if len(argv) < 4:
    print '''search.py [search type] [search term] [n° of results]'''
    exit()

IP = socket.gethostbyname(socket.gethostname())
if argv[1] in ['web', 'local', 'video', 'blogs', 'news', 'books', 'images', 'patent']:
    TYPE = argv[1]

if argv[2]:
    TERM = argv[2]

if argv[3]:
    AMOUNT = int(argv[3])
else:
    AMOUNT = 8

KEY = 'ABQIAAAAfTk2IdQA0Ey_Oe0O0lKpfBTRERdeAiwZ9EeJWta3L_JZVS0bOBSZbJCtMvSfc8Q6xD2JDIz-2ooVzA'

RESULTS = []

def getresults(size='large'):
    url = ('http://ajax.googleapis.com/ajax/services/search/%s'
       '?v=1.0&q=%s&key=%s&userip=%s&rsz=%s' % (TYPE, TERM.replace(' ', '%20'),
                    KEY, IP, size))

    request = urllib2.Request(url, None, {'Referer': 'http://www.google.com'})
    response = urllib2.urlopen(request)
    results = simplejson.load(response)
    return results

def remove_html_tags(data):
    p = re.compile(r'<[^<]*?/?>')
    return p.sub('', data)

class result:
    def __init__(self, dict):
        self.dict = dict
        
        self.searchclass = dict['GsearchResultClass']
        
        if self.searchclass == 'GblogSearch':
            self.visibleUrl = dict['blogUrl']
        elif not self.searchclass in ['GvideoSearch', 'GnewsSearch', 'GbookSearch', 'GpatentSearch']:
            self.visibleUrl = dict['visibleUrl']
        else:
            self.visibleUrl = None
        
        self.titleNoFormatting = dict['titleNoFormatting']
        
        self.title = dict['title']
        
        if self.searchclass == 'GblogSearch':
            self.url = dict['postUrl']
        else:
            self.url = dict['url']
        
        if self.searchclass not in ['GvideoSearch', 'GblogSearch']:
            self.unescapedUrl = dict['unescapedUrl']
        
        if self.searchclass != 'GbookSearch':
            self.content = dict['content']
        else:
            self.authors = dict['authors']
        
    def display(self):
        if self.searchclass == 'GimageSearch':
            webFile = urllib2.urlopen(self.unescapedUrl)
            
            import tempfile
            localFile = tempfile.NamedTemporaryFile('w', delete=False)
            localFile.write(webFile.read())
            
            webFile.close()
            
            filename = localFile.name
            localFile.close()
            
            import subprocess
            subprocess.Popen(['feh', localFile.name])
        elif self.searchclass in ['GvideoSearch', 'GblogSearch']:
            import webbrowser
            webbrowser.open(self.url, autoraise=True)
        else:
            import webbrowser
            webbrowser.open(self.unescapedUrl)

for x in range(0, ((AMOUNT + 7 ) / 8)):
    results = getresults(size='large')
    for y in range(0, 8):
        RESULTS.append(result(results['responseData']['results'][y]))
    
for result in RESULTS:
    if RESULTS.index(result) > AMOUNT - 1: break
    
    if not SEARCH: print '\033[1;43m%i.\033[1;m ' % RESULTS.index(result),
    
    print '\033[1;32m%s\033[1;m' % result.titleNoFormatting,
    
    if result.visibleUrl != None:
        print '| \033[1;37m%s\033[1;m' % result.visibleUrl
    elif result.searchclass == 'GbookSearch':
        print '| \033[1;37m%s\033[1;m' % remove_html_tags(result.authors)
    else:
        print ''
    
    if result.searchclass == 'GpatentSearch':
        print '\033[1;35mPatent n° %i awarded to %s on %s\033[1;m' % (int(result.dict['patentNumber']), result.dict['assignee'], 
                                                                                                                result.dict['applicationDate'])
    
    if result.searchclass != 'GbookSearch':
        print '\t%s' % remove_html_tags(result.content)

if SEARCH:
    exit()

while 1:
    choice = raw_input('\n\n\033[1;33m==>\033[1;m Enter n° of the uri to be opened\n\033[1;33m==>\033[1;m ')
    choice = int(choice)
    if choice < len(RESULTS): break
    print '\033[1;33mIndex out of range\033[1;33m'

RESULTS[choice].display()
