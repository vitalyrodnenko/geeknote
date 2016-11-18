# -*- coding: utf-8 -*-

import httplib
import time
import Cookie
import uuid
import re
from urllib import urlencode, unquote
from urlparse import urlparse
from lxml import html

import out
import tools
import config
from log import logging


class GeekNoteAuth(object):

    consumerKey = config.CONSUMER_KEY
    consumerSecret = config.CONSUMER_SECRET

    url = {
        "base": config.USER_BASE_URL,
        "oauth": "/OAuth.action?oauth_token=%s",
        "access": "/OAuth.action",
        "token" : "/oauth",
        "login" : "/Login.action",
        "tfa"   : "/OTCAuth.action",
    }

    cookies = {}

    postData = {
        'login': {
            'login': 'Sign in',
            'username': '',
            'password': '',
            'targetUrl': None,
        },
        'access': {
            'authorize': 'Authorize',
            'oauth_token': None,
            'oauth_callback': None,
            'embed': 'false',
            'expireMillis': '31536000000',
        },
        'tfa': {
            'code': '',
            'login': 'Sign in',
        },
    }

    username = None
    password = None
    tmpOAuthToken = None
    verifierToken = None
    OAuthToken = None
    incorrectLogin = 0
    incorrectCode = 0
    code = None

    def getTokenRequestData(self, **kwargs):
        params = {
            'oauth_consumer_key': self.consumerKey,
            'oauth_signature': self.consumerSecret + '%26',
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': uuid.uuid4().hex
        }

        if kwargs:
            params = dict(params.items() + kwargs.items())

        return params

    def loadPage(self, url, uri=None, method="GET", params="", additionalParams=""):
        if not url:
            logging.error("Request URL undefined")
            tools.exitErr()

        if not uri:
            urlData = urlparse(url)
            url = urlData.netloc
            uri = urlData.path + '?' + urlData.query

        # prepare params, append to uri
        if params:
            params = urlencode(params) + additionalParams
            if method == "GET":
                uri += ('?' if uri.find('?') == -1 else '&') + params
                params = ""

        # insert local cookies in request
        headers = {
            "Cookie": '; '.join([key + '=' + self.cookies[key] for key in self.cookies.keys()])
        }

        if method == "POST":
            headers["Content-type"] = "application/x-www-form-urlencoded"

        logging.debug("Request URL: %s:/%s > %s # %s", url,
                      uri, unquote(params), headers["Cookie"])

        conn = httplib.HTTPSConnection(url)
        conn.request(method, uri, params, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        logging.debug("Response : %s > %s",
                      response.status,
                      response.getheaders())
        result = tools.Struct(status=response.status,
                              location=response.getheader('location', None),
                              data=data)

        # update local cookies
        sk = Cookie.SimpleCookie(response.getheader("Set-Cookie", ""))
        for key in sk:
            self.cookies[key] = sk[key].value
        # delete cookies whose content is "deleteme"
        for key in self.cookies.keys():
            if self.cookies[key] == "deleteme":
                del self.cookies[key]

        return result

    def parseResponse(self, data):
        data = unquote(data)
        return dict(item.split('=', 1) for item in data.split('?')[-1].split('&'))

    def getToken(self):
        out.preloader.setMessage('Authorize...')
        self.getTmpOAuthToken()

        self.login()

        out.preloader.setMessage('Allow Access...')
        self.allowAccess()

        out.preloader.setMessage('Getting Token...')
        self.getOAuthToken()

        #out.preloader.stop()
        return self.OAuthToken

    def getTmpOAuthToken(self):
        response = self.loadPage(self.url['base'],
                                 self.url['token'],
                                 "GET",
                                 self.getTokenRequestData(
                                     oauth_callback="https://" + self.url['base']
                                 ))

        if response.status != 200:
            logging.error("Unexpected response status on get "
                          "temporary oauth_token 200 != %s", response.status)
            tools.exitErr()

        responseData = self.parseResponse(response.data)
        if 'oauth_token' not in responseData:
            logging.error("OAuth temporary not found")
            tools.exitErr()

        self.tmpOAuthToken = responseData['oauth_token']

        logging.debug("Temporary OAuth token : %s", self.tmpOAuthToken)

    def handleTwoFactor(self):
        self.code = out.GetUserAuthCode()
        self.postData['tfa']['code'] = self.code
        response = self.loadPage(self.url['base'], self.url['tfa']+";jsessionid="+self.cookies['JSESSIONID'], "POST", self.postData['tfa'])
        if not response.location and response.status == 200:
            if self.incorrectCode < 3:
                out.preloader.stop()
                out.printLine('Sorry, incorrect two factor code')
                out.preloader.setMessage('Authorize...')
                self.incorrectCode += 1
                return self.handleTwoFactor()
            else:
                logging.error("Incorrect two factor code")

        if not response.location:
            logging.error("Target URL was not found in the response on login")
            tools.exitErr()

    def login(self):
        response = self.loadPage(self.url['base'],
                                 self.url['login'],
                                 "GET",
                                 {'oauth_token': self.tmpOAuthToken})

        # parse hpts and hptsh from page content
        hpts = re.search('.*\("hpts"\)\.value.*?"(.*?)"', response.data)
        hptsh = re.search('.*\("hptsh"\)\.value.*?"(.*?)"', response.data)

        if response.status != 200:
            logging.error("Unexpected response status "
                          "on login 200 != %s", response.status)
            tools.exitErr()

        if 'JSESSIONID' not in self.cookies:
            logging.error("Not found value JSESSIONID in the response cookies")
            tools.exitErr()

        # get login/password
        self.username, self.password = out.GetUserCredentials()

        self.postData['login']['username'] = self.username
        self.postData['login']['password'] = self.password
        self.postData['login']['targetUrl'] = self.url['oauth'] % self.tmpOAuthToken
        self.postData['login']['hpts'] = hpts and hpts.group(1) or ""
        self.postData['login']['hptsh'] = hptsh and hptsh.group(1) or ""
        response = self.loadPage(self.url['base'],
                                 self.url['login'] + ";jsessionid=" + self.cookies['JSESSIONID'],
                                 "POST",
                                 self.postData['login'])

        if not response.location and response.status == 200:
            if self.incorrectLogin < 3:
                out.preloader.stop()
                out.printLine('Sorry, incorrect login or password')
                out.preloader.setMessage('Authorize...')
                self.incorrectLogin += 1
                return self.login()
            else:
                logging.error("Incorrect login or password")

        if not response.location:
            logging.error("Target URL was not found in the response on login")
            tools.exitErr()

        if response.status == 302:
            # the user has enabled two factor auth
            return self.handleTwoFactor()


        logging.debug("Success authorize, redirect to access page")

        #self.allowAccess(response.location)

    def allowAccess(self):
        response = self.loadPage(self.url['base'],
                                 self.url['access'],
                                 "GET",
                                 {'oauth_token': self.tmpOAuthToken})

        logging.debug(response.data)
        tree = html.fromstring(response.data);
        token = "&" + urlencode({ 'csrfBusterToken': tree.xpath("//input[@name='csrfBusterToken']/@value")[0]}) + "&" + urlencode({ 'csrfBusterToken': tree.xpath("//input[@name='csrfBusterToken']/@value")[1]})
        sourcePage = tree.xpath("//input[@name='_sourcePage']/@value")[0]
        fp = tree.xpath("//input[@name='__fp']/@value")[0]
        targetUrl = tree.xpath("//input[@name='targetUrl']/@value")[0]
        logging.debug(token);

        if response.status != 200:
            logging.error("Unexpected response status "
                          "on login 200 != %s", response.status)
            tools.exitErr()

        if 'JSESSIONID' not in self.cookies:
            logging.error("Not found value JSESSIONID in the response cookies")
            tools.exitErr()
        
        access = self.postData['access']
        access['oauth_token'] = self.tmpOAuthToken
        access['oauth_callback'] = ""
        access['embed'] = 'false'
        access['suggestedNotebookName'] = 'Geeknote'
        access['supportLinkedSandbox'] = ''
        access['analyticsLoginOrigin'] = 'Other'
        access['clipperFlow'] = 'false'
        access['showSwitchService'] = 'true'
        access['_sourcePage'] = sourcePage
        access['__fp'] = fp
        access['targetUrl'] = targetUrl

        response = self.loadPage(self.url['base'],
                                 self.url['access'],
                                 "POST", access, token)

        if response.status != 302:
            logging.error("Unexpected response status on allowing "
                          "access 302 != %s", response.status)
            logging.error(response.data)
            tools.exitErr()

        responseData = self.parseResponse(response.location)
        if 'oauth_verifier' not in responseData:
            logging.error("OAuth verifier not found")
            tools.exitErr()

        self.verifierToken = responseData['oauth_verifier']

        logging.debug("OAuth verifier token take")

        #self.getOAuthToken(verifier)

    def getOAuthToken(self):
        response = self.loadPage(self.url['base'],
                                 self.url['token'],
                                 "GET",
                                 self.getTokenRequestData(
                                     oauth_token=self.tmpOAuthToken,
                                     oauth_verifier=self.verifierToken))

        if response.status != 200:
            logging.error("Unexpected response status on "
                          "getting oauth token 200 != %s", response.status)
            tools.exitErr()

        responseData = self.parseResponse(response.data)
        if 'oauth_token' not in responseData:
            logging.error("OAuth token not found")
            tools.exitErr()

        logging.debug("OAuth token take : %s", responseData['oauth_token'])
        self.OAuthToken = responseData['oauth_token']
