# coding: utf-8
from oauth import escape, OAuthError
from oauth.signature_method.base import OAuthSignatureMethod
from tlslite.utils import keyfactory
import base64


class OAuthSignatureMethod_RSA_SHA1(OAuthSignatureMethod):
    """
    Implements the RSA-SHA1 signature logic.

    http://oauth.net/core/1.0/#rfc.section.9.3

    This is not a concrete implementation. An implementation needs to provide a
    public_cert and a private_cert.

    """
    name = 'RSA-SHA1'

    @property
    def public_cert(self):
        """
        The public certificate used for validating signatures.

        *An implementation needs to provide this.*

        """
        raise NotImplementedError

    @property
    def private_cert(self):
        """
        The private certificate used for signing requests.

        *An implementation needs to provide this.*

        """
        raise NotImplementedError

    @property
    def signature(self):
        privatekey = keyfactory.parsePrivateKey(self.private_cert)
        signature = privatekey.hashAndSign(self.base_string)
        return base64.b64encode(signature)

    def validate_signature(self, signature):
        decoded_sig = base64.b64decode(signature)
        publickey = keyfactory.parsePEMKey(self.public_cert, public=True)
        if not publickey.hashAndVerify(decoded_sig, self.base_string):
            raise OAuthError('Invalid Signature')
