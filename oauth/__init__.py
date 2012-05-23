# coding: utf-8
import collections
import random
import time
import urllib
import urlparse
from urlencoding import escape, parse_qs, compose_qs


OAUTH_VERSION = '1.0'
TIMESTAMP_THRESHOLD = 300
NONCE_LENGTH = 10

class OAuthError(RuntimeError):
    """
    Generic OAuthError for all error cases.

    """
    pass

class OAuthRequest(object):
    """
    Represents outgoing or incoming requests. Provides the ability to sign
    outgoing requests (`sign_request <#oauth.OAuthRequest.sign_request>`_), and
    validate incoming signed requests (`validate_signature
    <#oauth.OAuthRequest.validate_signature>`_).

    Arguments:

        `url`
            The URL. Query parameters in the URL will automatically be parsed
            out. **Required**.

        `http_method`
            The HTTP method for the request.

        `params`
            A dict or string body of request parameters.

        `headers`
            A dict which may contain the *Authorization* header.

        `version`
            The *oauth_version*.

        `timestamp_threshold`
            The number of seconds a received timestamp can be off by.

        `nonce_length`
            The length of the randomly generated nonce.

    """

    def __init__(self, url, http_method='GET', params=None, headers={},
            version=OAUTH_VERSION, timestamp_threshold=TIMESTAMP_THRESHOLD,
            nonce_length=NONCE_LENGTH):
        if params and not isinstance(params, collections.Mapping):
            # if its not a mapping, it must be a string
            params = parse_qs(params)
        elif not params:
            params = {}

        if 'Authorization' in headers:
            auth_header = headers['Authorization']
            # check that the authorization header is OAuth
            if auth_header.index('OAuth') > -1:
                try:
                    header_params = OAuthRequest._parse_auth_header(auth_header)
                    params.update(header_params)
                except ValueError:
                    raise OAuthError('Unable to parse OAuth parameters from Authorization header.')

        # URL parameters
        parts = urlparse.urlparse(url)
        url = '%s://%s%s' % (parts.scheme, parts.netloc, parts.path)
        params.update(parse_qs(parts.query)) #FIXME should this be a merge?

        self.http_method = http_method.upper()
        self.url = url
        self.params = params.copy()
        self.version = version
        self.timestamp_threshold = timestamp_threshold
        self.nonce_length = nonce_length

    def validate_signature(self, signature_method, consumer, token=None):
        """
        Validates an *existing* signature in the request. It does not return a
        value, and will throw an OAuthError exception when it fails.

        **BE WARNED**: Nonce validation is left to the user.
            http://oauth.net/core/1.0/#nonce


        Arguments:

        `signature_method`
            The class used to handle Signature logic. This should be a concrete
            implementation of `OAuthSignatureMethod
            <#oauth.signature_method.base.OAuthSignatureMethod>`_.

        `consumer`
            A dict containing the oauth_token and oauth_token_secret
            representing a OAuth Consumer.

        `token`
            An optional dict containing the oauth_token and oauth_token_secret
            representing a OAuth Token to be used in validating the signature.

        This is the basic usage flow for validating signatures:

         #. Create a Request object
         #. Create a dict with the OAuth Consumer information
         #. *Optionally* create a dict with the OAuth Token information
         #. Call validate_signature with the Signature Implementation, Consumer
            and optional Token and catch OAuthError exceptions.

        >>> from oauth import OAuthRequest
        >>> from oauth.signature_method.plaintext import OAuthSignatureMethod_PLAINTEXT
        >>> import time
        >>> params = {
                'oauth_nonce': '9747278682',
                'oauth_timestamp': str(int(time.time())),
                'oauth_consumer_key': 'my-ck',
                'oauth_signature_method': 'PLAINTEXT',
                'oauth_version': '1.0',
                'oauth_signature': 'my-cks%26',
            }
        >>> consumer = {'oauth_token': 'my-ck', 'oauth_token_secret': 'my-cks'}
        >>> request = OAuthRequest('https://example.org/get-request-token', 'GET', params)
        >>> request.validate_signature(OAuthSignatureMethod_PLAINTEXT, consumer)

        """
        try:
            sig = signature_method(self, consumer, token)

            timestamp = int(self.params['oauth_timestamp'])
            now = int(time.time())
            off_by = abs(now - timestamp)
            if off_by > self.timestamp_threshold:
                raise OAuthError('Expired timestamp: Given Time: %d | Server Time: %s | Threshold: %d.' % (timestamp, now, self.timestamp_threshold))

            if self.params['oauth_signature_method'] != sig.name:
                raise OAuthError('Unexpected oauth_signature_method. Was expecting %s.' % sig.name)

            sig.validate_signature(self.params['oauth_signature'])
        except KeyError:
            raise OAuthError('Missing required parameter')

    def sign_request(self, signature_method, consumer, token=None):
        """
        Generate a *new* signature adding/replacing a number of oauth_
        parameters as part of the process. Use this when you are making
        outbound signed requests.

        Arguments:

        `signature_method`
            The class used to handle Signature logic. This should be a concrete
            implementation of `OAuthSignatureMethod
            <#oauth.signature_method.base.OAuthSignatureMethod>`_.

        `consumer`
            A dict containing the oauth_token and oauth_token_secret
            representing a OAuth Consumer.

        `token`
            An optional dict containing the oauth_token and oauth_token_secret
            representing a OAuth Token to be used in signing the request.

        This is the basic usage flow for generating signatures:

         #. Create a Request object
         #. Create a dict with the OAuth Consumer information
         #. *Optionally* create a dict with the OAuth Token information
         #. Call sign_request with the Signature Implementation, Consumer and
            optional Token.

        >>> from oauth import OAuthRequest
        >>> from oauth.signature_method.hmac_sha1 import OAuthSignatureMethod_HMAC_SHA1
        >>> consumer = {'oauth_token': 'my-ck', 'oauth_token_secret': 'my-cks'}
        >>> request = OAuthRequest('http://example.org/get-request-token')
        >>> request.sign_request(OAuthSignatureMethod_HMAC_SHA1, consumer)
        >>> header = request.to_header()

        *header* will now contain the string that can be used as the
        *Authorization* header for this request.

        """
        sig = signature_method(self, consumer, token)

        self.params.update({
            'oauth_consumer_key': consumer['oauth_token'],
            'oauth_nonce': ''.join([str(random.randint(0, 9)) for i in range(self.nonce_length)]),
            'oauth_signature_method': sig.name,
            'oauth_timestamp': int(time.time()),
            'oauth_version': self.version,
        })
        if token and 'oauth_token' in token:
            self.params['oauth_token'] = token['oauth_token']

        self.params['oauth_signature'] = sig.signature

    def to_header(self, realm=None):
        """
        Generates the Authorization header with the current OAuth parameters.

        http://oauth.net/core/1.0/#auth_header

        Arguments:

        `realm`
            An optional string to use as as the realm. If missing, realm will
            be ommitted all together.

        """
        auth_header = 'OAuth '
        if realm:
            auth_header += 'realm="%s",' % realm
        oauth_params = dict([(k, v) for k, v in self.params.iteritems() if k[:6] == 'oauth_'])
        auth_header += compose_qs(oauth_params, pattern='%s="%s"', join=',')
        return auth_header

    def to_url(self, include_oauth=False):
        """
        Generates a URL suitable for a GET request.

        Arguments:

        `include_oauth`
            Decides if *oauth_* parameters are included. This is useful if the
            OAuth parameters are being sent via the query string in the URL
            instead of the Authorization header.

        """
        return '%s?%s' % (self.url, self.to_postdata(include_oauth))

    def to_postdata(self, include_oauth=False):
        """
        Generates the POST body.

        Arguments:

        `include_oauth`
            Decides if *oauth_* parameters are included. This is useful if the
            OAuth parameters are being sent via the POST body instead of the
            Authorization header.

        """
        if include_oauth:
            params = self.params
        else:
            params = dict([(k, v) for k, v in self.params.iteritems() if k[:6] != 'oauth_'])
        return compose_qs(params)

    @property
    def normalized_request_params(self):
        """
        Generates the normalized request parameters.

        http://oauth.net/core/1.0/#rfc.section.9.1.1

        """
        params = self.params.copy()
        params.pop('oauth_signature', None)
        return compose_qs(params, sort=True)

    @staticmethod
    def _parse_auth_header(header):
        """
        Parses the OAuth Authorization header:
            http://oauth.net/core/1.0/#auth_header

        Note: "realm" is dropped.

        """
        # drop OAuth prefix
        if header[:6].lower() == 'oauth ':
            header = header[6:]

        params = {}
        parts = header.split(',')
        for param in parts:
            key, value = param.strip().split('=', 1)
            if key == 'realm':
                continue
            params[key] = urllib.unquote(value.strip('"'))
        return params
