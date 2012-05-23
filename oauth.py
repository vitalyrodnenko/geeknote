# -*- coding: utf-8 -*-
# add oauth

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EVERNOTE_SDK = os.path.join(PROJECT_ROOT, 'oauth')
sys.path.append( EVERNOTE_SDK )


import httplib
import time
from urllib import quote_plus, urlencode
from urlparse import urlparse
import re

def getPage(url, uri=None, method="GET", params="", headers={}):
    if not uri:
        urlData = urlparse(url)
        url = urlData.netloc
        uri = urlData.path + '?' + urlData.query

    if params:
        params = urlencode(params)
        print params

    print uri
    conn = httplib.HTTPSConnection(url)
    conn.request(method, uri, params, headers)
    r = conn.getresponse()
    ret = {'resp': r, 'headers': r.getheaders(), 'data': r.read()}
    conn.close()
    return ret


CONSUMER_KEY = 'stepler'
CONSUMER_SECRET = 'de89e76dd1bf6e19'
POST_DATA = {
    'login': 'Sign in',
    'username': 'stepler',
    'password': '5t3pl3r',
    'targetUrl': None,
}
COOKIE = ""

baseUrl = 'sandbox.evernote.com'
tokenUrl = "/oauth?oauth_consumer_key=%(key)s&oauth_signature=%(s_key)s&oauth_signature_method=PLAINTEXT&oauth_timestamp=%(time)s&oauth_nonce=%(nonce)s&oauth_callback=%(callback)s"
authUrl = "/OAuth.action?oauth_token=%(token)s"
loginUrl = "/Login.action;jsessionid=%(jsessionid)s"

"""
conn = httplib.HTTPSConnection(baseUrl)
conn.request("GET", tokenUrl % {'key': CONSUMER_KEY, 's_key': CONSUMER_SECRET+'%26', 'time': str(int(time.time())), 'nonce': '1c4fbbe4387a685829d5938a3d97988c', 'callback': quote_plus('http://www.evernote.com')})

r = conn.getresponse()
resp = r.read()
conn.close()

#resp = 'oauth_token=stepler.13779C1B2FC.687474703A2F2F7777772E657665726E6F74652E636F6D.7517FB1D6F650595E5A95D91E2D86306&oauth_token_secret=&oauth_callback_confirmed=true'

oauth_token = re.search('oauth_token=(.*?)&', resp).group(1)
"""
oauth_token = 'stepler.13779C71548.687474703A2F2F7777772E657665726E6F74652E636F6D.51C73959902B94203AD1E31436CDA6C4'
print oauth_token

auth = getPage(baseUrl, authUrl % {'token': oauth_token});
print auth

if auth['resp'].status == 302:
    redirectUrl = auth['resp'].getheader('Location', None)
    if not redirectUrl:
        print 'error'
        exit(1)

    login = getPage(redirectUrl)
    print redirectUrl
    COOKIE = re.search('JSESSIONID=(.*?);', login['resp'].getheader('Set-Cookie', "")).group(1)


    POST_DATA['targetUrl'] = authUrl % {'token': oauth_token}
    #POST_DATA['_sourcePage'] = re.findall('_sourcePage\" value=\"(.*?)\"', login['data'])[-1]
    #POST_DATA['__fp'] = re.findall('__fp\" value=\"(.*?)\"', login['data'])[-1]
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        #"Cookie": "JSESSIONID=%s; cookieTestValue=%s" % (COOKIE, re.search('cookieTestValue=(.*?);', login['resp'].getheader('Set-Cookie', "")).group(1))
    }
    print headers
    print POST_DATA
    auth = getPage(baseUrl, loginUrl % {'jsessionid': COOKIE}, "POST", POST_DATA, headers)
    print auth
    print auth['data']

    redirectUrl = auth['resp'].getheader('Location', None)
    access = getPage(redirectUrl)
    print access