# coding: utf-8
from oauth import escape, OAuthError


class OAuthSignatureMethod(object):
    """
    The base signature method class. An implementation needs to provide a name
    and a signature. The default validate_signature compares a newly generated
    signature.

    http://oauth.net/core/1.0/#signing_process

    Arguments:

        `request`
            An instance of an OAuthRequest object.

        `consumer`
            A dict containing the oauth_token and oauth_token_secret
            representing a OAuth Consumer.

        `token`
            An optional dict containing the oauth_token and oauth_token_secret
            representing a OAuth Token to be used in signing the request.

    """

    def __init__(self, request, consumer={}, token={}):
        """
        Initialize an instance to handle a request.

         - request: a OAuthRequest object
         - consumer: a dict with a key/secret
         - token: a dict with a key/secret

        """

        self.request = request
        self.consumer = consumer
        self.token = token

    @property
    def name(self):
        """
        An implementation should provide an attribute called name for use as
        the *oauth_signature_method* value.

        """
        raise NotImplementedError

    @property
    def signature(self):
        """
        The core *oauth_signature* generating logic.

        """
        raise NotImplementedError

    def validate_signature(self, signature):
        """
        Checks if the given signature is valid. Default behaviour is to
        generate a new signature and compare it to the given one. Raises an
        OAuthError if the signatures do not match.

        Arguments:

            `signature`
                The signature to validate.

        """
        if self.signature != signature:
            raise OAuthError('Invalid Signature')

    @property
    def base_secrets(self):
        """
        Returns the concatenated encoded values of the Consumer Secret and
        Token Secret, separated by a ‘&’ character (ASCII code 38), even if
        either secret is empty.

        """

        key = ''
        if self.consumer and 'oauth_token_secret' in self.consumer:
            key += escape(self.consumer['oauth_token_secret'])
        key += '&'
        if self.token and 'oauth_token_secret' in self.token:
            key += escape(self.token['oauth_token_secret'])

        return key

    @property
    def base_string(self):
        """
        Generates the Signature Base String.

        http://oauth.net/core/1.0/#rfc.section.A.5.1

        """

        return '&'.join((
            escape(self.request.http_method),
            escape(self.request.url),
            escape(self.request.normalized_request_params),
        ))
