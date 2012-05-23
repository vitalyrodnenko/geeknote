# coding: utf-8
from oauth import escape
from oauth.signature_method.base import OAuthSignatureMethod


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):
    """
    Implements the PLAINTEXT signature logic.

    http://oauth.net/core/1.0/#rfc.section.9.4

    """
    name = 'PLAINTEXT'

    @property
    def signature(self):
        return self.base_secrets
