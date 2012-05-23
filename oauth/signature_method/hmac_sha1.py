# coding: utf-8
from oauth import escape
from oauth.signature_method.base import OAuthSignatureMethod
import binascii
import hashlib
import hmac


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):
    """
    Implements the HMAC-SHA1 signature logic.

    http://oauth.net/core/1.0/#rfc.section.9.2

    """
    name = 'HMAC-SHA1'

    @property
    def signature(self):
        hashed = hmac.new(self.base_secrets, self.base_string, hashlib.sha1)
        return binascii.b2a_base64(hashed.digest())[:-1]
