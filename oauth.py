# -*- coding: utf-8 -*-
# add oauth

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EVERNOTE_SDK = os.path.join(PROJECT_ROOT, 'oauth')
sys.path.append( EVERNOTE_SDK )


import httplib
import time
from urllib import quote_plus, urlencode, unquote
from urlparse import urlparse
import re
import Cookie
import uuid


CONSUMER_KEY = 'stepler'
CONSUMER_SECRET = 'de89e76dd1bf6e19'
LOGIN_POST_DATA = {
    'login': 'Sign in',
    'username': 'stepler',
    'password': '5t3pl3r',
    'targetUrl': None,
}
ACCESS_POST_DATA = {
    'authorize': 'Authorize',
    'oauth_token': None,
    'oauth_callback': None,
    'embed': 'false',
}
COOKIES = {}

baseUrl  = 'sandbox.evernote.com'
authUrl  = "/OAuth.action?oauth_token=%(token)s"
loginUrl = "/Login.action;jsessionid=%(jsessionid)s"
accesshUrl = "/OAuth.action"
oauthUrl = "/oauth"

class auth(object):

    url = {
        "base"  : "sandbox.evernote.com",
        "oauth" : "/OAuth.action",
        "login" : "/Login.action;jsessionid=%(jsessionid)s"
    }

    cookies = {}

    postData = {
        'login': {
            'login': 'Sign in',
            'username': 'stepler',
            'password': '5t3pl3r',
            'targetUrl': None,
        },
        access: {
            'authorize': 'Authorize',
            'oauth_token': None,
            'oauth_callback': None,
            'embed': 'false',
        }
    }

    tmpOAuthToken = None

    def getTokenRequestData(self, **kwargs):
        params = {
            'oauth_consumer_key': CONSUMER_KEY, 
            'oauth_signature': CONSUMER_SECRET+'%26', 
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())), 
            'oauth_nonce': uuid.uuid4().hex
        }
    
    def loadPage(self, url, uri=None, method="GET", params=""):
        if not url:
            print "ERROR: URL NOT FOUND"
            exit(1)

        if not uri:
            urlData = urlparse(url)
            url = urlData.netloc
            uri = urlData.path + '?' + urlData.query

        if params:
            params = urlencode(params)
            if method == "GET":
                uri += ( '?' uri.find('?') == -1 '&') + params
                params = ""

        # insert local cookies in request
        headers = {
            "Cookie": '; '.join( [ key+'='+self.cookies[key] for key in self.cookies.keys() ] )
        }

        if method == "POST":
            headers["Content-type"] = "application/x-www-form-urlencoded"

        
        conn = httplib.HTTPSConnection(url)
        conn.request(method, uri, params, headers)
        response = conn.getresponse()

        result = new Struct(status=response.status, headers=response.getheaders(), data=response.read())
        conn.close()

        # update local cookies
        sk = Cookie.SimpleCookie(response.getheaders("Set-Cookie", ""))
        self.cookies[key] = sk[key].value for key in sk:

        return result


    def run(self):
        pass

    def getTmpOAuthToken(self):
        response = self.loadPage(self.url['base'], self.url['oauth'], "GET", 
            self.getTokenRequestData(oauth_callback="https://"+elf.url['base']))

        if (response.status != 302)
            raise Exeption('ERROR')

        self.tmpOAuthToken = re.search('oauth_token=(.*?)&', response.data).group(1)

        # AUTH 
        auth = getPage(baseUrl, authUrl % {'token': oauth_token});
        redirectUrl = auth['resp'].getheader('Location', None)

        # LOGIN
        login = getPage(redirectUrl)

        # AUTH 
        LOGIN_POST_DATA['targetUrl'] = authUrl % {'token': oauth_token}
        auth = getPage(baseUrl, loginUrl % {'jsessionid': COOKIES['JSESSIONID']}, "POST", LOGIN_POST_DATA)

        # ALLOW ACCESS
        redirectUrl = auth['resp'].getheader('Location', None)
        access = getPage(redirectUrl)

        ACCESS_POST_DATA['oauth_token'] = oauth_token
        ACCESS_POST_DATA['oauth_callback'] = baseUrl
        allow_access = getPage(baseUrl, accesshUrl, "POST", ACCESS_POST_DATA)

        # GET REAL TOKEN
        real_oauth_token = getPage(baseUrl, oauthUrl, "GET", {
            'oauth_consumer_key': CONSUMER_KEY, 
            'oauth_signature': CONSUMER_SECRET+'%26', 
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())), 
            'oauth_nonce': '1c4fbbe4387a685829d5938a3d97988b',
            'oauth_token': oauth_token,
            'oauth_verifier': re.search('oauth_verifier=(.*)$', allow_access['resp'].getheader('Location', '')).group(1)
        })

print unquote(real_oauth_token['data'])



class Struct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)


def getPage(url, uri=None, method="GET", params=""):
    if not url:
        print "ERROR: URL NOT FOUND"
        exit(1)

    if not uri:
        urlData = urlparse(url)
        url = urlData.netloc
        uri = urlData.path + '?' + urlData.query

    if params:
        params = urlencode(params)
        print params

    if params and method == "GET":
        uri += '?' + params
        params = ""

    headers = {
        "Cookie": getCookie()
    }

    if method == "POST":
        headers["Content-type"] = "application/x-www-form-urlencoded"

    print uri
    print headers
    conn = httplib.HTTPSConnection(url)
    conn.request(method, uri, params, headers)
    r = conn.getresponse()
    ret = {'resp': r, 'headers': r.getheaders(), 'data': r.read()}
    conn.close()

    setCookie(r.getheader('Set-Cookie', ""))

    print ret
    print "---"
    return ret

def setCookie(setCookies):
    sk = Cookie.SimpleCookie(setCookies)
    for key in sk:
        COOKIES[key] = sk[key].value

def getCookie():
    return '; '.join([key+'='+COOKIES[key] for key in COOKIES.keys()])

CONSUMER_KEY = 'stepler'
CONSUMER_SECRET = 'de89e76dd1bf6e19'
LOGIN_POST_DATA = {
    'login': 'Sign in',
    'username': 'stepler',
    'password': '5t3pl3r',
    'targetUrl': None,
}
ACCESS_POST_DATA = {
    'authorize': 'Authorize',
    'oauth_token': None,
    'oauth_callback': None,
    'embed': 'false',
}
COOKIES = {}

baseUrl  = 'sandbox.evernote.com'
authUrl  = "/OAuth.action?oauth_token=%(token)s"
loginUrl = "/Login.action;jsessionid=%(jsessionid)s"
accesshUrl = "/OAuth.action"
oauthUrl = "/oauth"


# AUTH TOKEN
token = getPage(baseUrl, tokenUrl, "GET", {
    'oauth_consumer_key': CONSUMER_KEY, 
    'oauth_signature': CONSUMER_SECRET+'%26', 
    'oauth_signature_method': 'PLAINTEXT',
    'oauth_timestamp': str(int(time.time())), 
    'oauth_nonce': '1c4fbbe4387a685829d5938a3d97988c',
    'oauth_callback': baseUrl
})
oauth_token = re.search('oauth_token=(.*?)&', token['data']).group(1)

# AUTH 
auth = getPage(baseUrl, authUrl % {'token': oauth_token});
redirectUrl = auth['resp'].getheader('Location', None)

# LOGIN
login = getPage(redirectUrl)

# AUTH 
LOGIN_POST_DATA['targetUrl'] = authUrl % {'token': oauth_token}
auth = getPage(baseUrl, loginUrl % {'jsessionid': COOKIES['JSESSIONID']}, "POST", LOGIN_POST_DATA)

# ALLOW ACCESS
redirectUrl = auth['resp'].getheader('Location', None)
access = getPage(redirectUrl)

ACCESS_POST_DATA['oauth_token'] = oauth_token
ACCESS_POST_DATA['oauth_callback'] = baseUrl
allow_access = getPage(baseUrl, accesshUrl, "POST", ACCESS_POST_DATA)

# GET REAL TOKEN
real_oauth_token = getPage(baseUrl, oauthUrl, "GET", {
    'oauth_consumer_key': CONSUMER_KEY, 
    'oauth_signature': CONSUMER_SECRET+'%26', 
    'oauth_signature_method': 'PLAINTEXT',
    'oauth_timestamp': str(int(time.time())), 
    'oauth_nonce': '1c4fbbe4387a685829d5938a3d97988b',
    'oauth_token': oauth_token,
    'oauth_verifier': re.search('oauth_verifier=(.*)$', allow_access['resp'].getheader('Location', '')).group(1)
})

print unquote(real_oauth_token['data'])