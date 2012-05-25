# -*- coding: utf-8 -*-
# add oauth

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EVERNOTE_SDK = os.path.join(PROJECT_ROOT, 'oauth')
sys.path.append( EVERNOTE_SDK )

import httplib
from log import logging
import time
from urllib import quote_plus, urlencode, unquote
from urlparse import urlparse
import re
import Cookie
import uuid

CONSUMER_KEY = 'stepler'
CONSUMER_SECRET = 'de89e76dd1bf6e19'

class Struct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

class AuthError(Exception):
    """Base class for exceptions in this module."""
    pass

class auth(object):

    url = {
        "base"  : "sandbox.evernote.com",
        "oauth" : "/OAuth.action?oauth_token=%s",
        "access": "/OAuth.action",
        "token" : "/oauth",
        "login" : "/Login.action;jsessionid=%s"
    }

    cookies = {}

    postData = {
        'login': {
            'login': 'Sign in',
            'username': 'stepler',
            'password': '5t3pl3r',
            'targetUrl': None,
        },
        'access': {
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

        if kwargs:
            params = dict(params.items() + kwargs.items())
        
        return params
    
    def loadPage(self, url, uri=None, method="GET", params=""):
        if not url:
            logging.error("Request URL undefined")
            exit(1)

        if not uri:
            urlData = urlparse(url)
            url = urlData.netloc
            uri = urlData.path + '?' + urlData.query

        if params :
            params = urlencode(params)
            if method == "GET":
                uri += ('?' if uri.find('?') == -1 else '&') + params
                params = ""

        # insert local cookies in request
        headers = {
            "Cookie": '; '.join( [ key+'='+self.cookies[key] for key in self.cookies.keys() ] )
        }

        if method == "POST":
            headers["Content-type"] = "application/x-www-form-urlencoded"

        logging.debug("Request URL: %s:/%s > %s # %s", url, uri, unquote(params), headers["Cookie"])

        conn = httplib.HTTPSConnection(url)
        conn.request(method, uri, params, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        logging.debug("Response : %s > %s", response.status, response.getheaders())
        result = Struct(status=response.status, location=response.getheader('location', None), data=data)

        # update local cookies
        sk = Cookie.SimpleCookie(response.getheader("Set-Cookie", ""))
        for key in sk:
            self.cookies[key] = sk[key].value

        return result

    def parseResponse(self, data):
        data = unquote(data)
        return dict( item.split('=', 1) for item in data.split('?')[-1].split('&') )


    def run(self):
        self.getTmpOAuthToken()

    def getTmpOAuthToken(self):
        response = self.loadPage(self.url['base'], self.url['token'], "GET", 
            self.getTokenRequestData(oauth_callback="https://"+self.url['base']))

        if response.status != 200:
            logging.error("Unexpected response status on get temporary oauth_token 200 != %s", response.status)
            exit(1)

        responseData = self.parseResponse(response.data)
        if not responseData.has_key('oauth_token'):
            logging.error("OAuth temporary not found")
            exit(1)

        self.tmpOAuthToken = responseData['oauth_token']

        logging.debug("Temporary OAuth token : %s", self.tmpOAuthToken)

        self.tryAuth()

    def tryAuth(self):
        response = self.loadPage(self.url['base'], self.url['oauth']%self.tmpOAuthToken)

        if response.status != 302:
            logging.error("Unexpected response status on oauth 302 != %s", response.status)
            exit(1)

        if not response.location:
            logging.error("Target URL was not found in the response")
            exit(1)

        logging.debug("Redirect on login page")

        self.login(response.location)

    def login(self, URL):
        response = self.loadPage(URL)

        if response.status != 200:
            logging.error("Unexpected response status on login 200 != %s", response.status)
            exit(1)

        if not self.cookies.has_key('JSESSIONID'):
            logging.error("Not found value JSESSIONID in the response cookies")
            exit(1)

        self.postData['login']['targetUrl'] = self.url['oauth']%self.tmpOAuthToken
        response = self.loadPage(self.url['base'], self.url['login']%self.cookies['JSESSIONID'], "POST", self.postData['login'])

        if not response.location:
            logging.error("Target URL was not found in the response on login")
            exit(1)

        if response.location.find('Login.action') != -1:
            logging.error("Incorrect login or password")
            print response.data
            exit(1)

        logging.debug("Success authorize, redirect to access page")

        self.allowAccess(response.location)

    def allowAccess(self, URL):
        response = self.loadPage(URL)

        if response.status != 200:
            logging.error("Unexpected response status on allowing access 200 != %s", response.status)
            exit(1)

        self.postData['access']['oauth_token'] = self.tmpOAuthToken
        self.postData['access']['oauth_callback'] = "https://"+self.url['base']
        response = self.loadPage(self.url['base'], self.url['access'], "POST", self.postData['access'])

        if response.status != 302:
            logging.error("Unexpected response status on allowing access 302 != %s", response.status)
            exit(1)

        responseData = self.parseResponse(response.location)
        if not responseData.has_key('oauth_verifier'):
            logging.error("OAuth verifier not found")
            exit(1)

        verifier = responseData['oauth_verifier']

        logging.debug("OAuth verifier token take")

        self.getOAuthToken(verifier)

    def getOAuthToken(self, verifier):
        response = self.loadPage(self.url['base'], self.url['token'], "GET",  
            self.getTokenRequestData(oauth_token=self.tmpOAuthToken, oauth_verifier=verifier))

        if response.status != 200:
            logging.error("Unexpected response status on getting oauth token 200 != %s", response.status)
            exit(1)

        responseData = self.parseResponse(response.data)
        if not responseData.has_key('oauth_token'):
            logging.error("OAuth token not found")
            exit(1)

        logging.debug("OAuth token take : %s", responseData['oauth_token'])
        print responseData['oauth_token']

A = auth()
A.run()
"""
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
"""