# -*- coding: utf-8 -*-

import httplib
import time
import Cookie
import uuid
from log import logging
from urllib import urlencode, unquote
from urlparse import urlparse

import io

CONSUMER_KEY = 'stepler-8439'
CONSUMER_SECRET = '4b4e6661ed1f2a5c'

class Struct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

class AuthError(Exception):
    """Base class for exceptions in this module."""
    pass

class GeekNoteAuth(object):

    url = {
        "base"  : "sandbox.evernote.com",
        "oauth" : "/OAuth.action?oauth_token=%s",
        "access": "/OAuth.action",
        "token" : "/oauth",
        "login" : "/Login.action",
        #"login" : "/Login.action;jsessionid=%s"
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

    username = None
    password = None
    tmpOAuthToken = None
    verifierToken = None
    OAuthToken = None
    incorrectLogin = 0


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

        # prepare params, append to uri
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


    def getToken(self):
        io.preloader.setMessage('Login...')
        self.getTmpOAuthToken()

        io.preloader.setMessage('Authorize...')
        self.login()

        io.preloader.setMessage('Allow Access...')
        self.allowAccess()

        io.preloader.setMessage('Getting Token...')
        self.getOAuthToken()

        #io.preloader.stop()
        return self.OAuthToken


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

    def login(self):
        response = self.loadPage(self.url['base'], self.url['login'], "GET", {'oauth_token': self.tmpOAuthToken})

        if response.status != 200:
            logging.error("Unexpected response status on login 200 != %s", response.status)
            exit(1)

        if not self.cookies.has_key('JSESSIONID'):
            logging.error("Not found value JSESSIONID in the response cookies")
            exit(1)

        # get login/password
        self.username, self.password = io.GetUserCredentials()

        self.postData['login']['username'] = self.username
        self.postData['login']['password'] = self.password
        self.postData['login']['targetUrl'] = self.url['oauth']%self.tmpOAuthToken
        response = self.loadPage(self.url['base'], self.url['login']+";jsessionid="+self.cookies['JSESSIONID'], "POST", 
            self.postData['login'])

        if not response.location and response.status == 200:
            if self.incorrectLogin < 3:
                return self.login()
            else:
                logging.error("Incorrect login or password")

        if not response.location:
            logging.error("Target URL was not found in the response on login")
            exit(1)

        logging.debug("Success authorize, redirect to access page")

        #self.allowAccess(response.location)

    def allowAccess(self):

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

        self.verifierToken = responseData['oauth_verifier']

        logging.debug("OAuth verifier token take")

        #self.getOAuthToken(verifier)

    def getOAuthToken(self):
        response = self.loadPage(self.url['base'], self.url['token'], "GET",  
            self.getTokenRequestData(oauth_token=self.tmpOAuthToken, oauth_verifier=self.verifierToken))

        if response.status != 200:
            logging.error("Unexpected response status on getting oauth token 200 != %s", response.status)
            exit(1)

        responseData = self.parseResponse(response.data)
        if not responseData.has_key('oauth_token'):
            logging.error("OAuth token not found")
            exit(1)

        logging.debug("OAuth token take : %s", responseData['oauth_token'])
        self.OAuthToken = responseData['oauth_token']