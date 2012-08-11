# -*- coding: utf-8 -*-

"""
From old version API
"""

from evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException
import evernote.edam.userstore.UserStore as UserStore
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
from thrift.Thrift import TType, TMessageType
from thrift.transport import TTransport
try:
    from thrift.protocol import fastbinary
except:
    fastbinary = None


class getNoteStoreUrl_args(object):
    """
    Attributes:
     - authenticationToken
    """

    thrift_spec = (None, (1, TType.STRING, 'authenticationToken', None, None, ), )

    def __init__(self, authenticationToken=None,):
        self.authenticationToken = authenticationToken

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 1:
                if ftype == TType.STRING:
                    self.authenticationToken = iprot.readString()
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
            oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
            return
        oprot.writeStructBegin('getNoteStoreUrl_args')
        if self.authenticationToken is not None:
            oprot.writeFieldBegin('authenticationToken', TType.STRING, 1)
            oprot.writeString(self.authenticationToken)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class getNoteStoreUrl_result(object):
    """
    Attributes:
     - success
     - userException
     - systemException
    """

    thrift_spec = (
        (0, TType.STRING, 'success', None, None,),
        (1, TType.STRUCT, 'userException', (EDAMUserException,
                                            EDAMUserException.thrift_spec), None,),
        (2, TType.STRUCT, 'systemException', (EDAMSystemException, EDAMSystemException.thrift_spec), None,)
    )

    def __init__(self, success=None, userException=None, systemException=None,):
        self.success = success
        self.userException = userException
        self.systemException = systemException

    def read(self, iprot):
        if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
            fastbinary.decode_binary(self, iprot.trans,
                                     (self.__class__, self.thrift_spec))
            return
        iprot.readStructBegin()
        while True:
            (fname, ftype, fid) = iprot.readFieldBegin()
            if ftype == TType.STOP:
                break
            if fid == 0:
                if ftype == TType.STRING:
                    self.success = iprot.readString()
                else:
                    iprot.skip(ftype)
            elif fid == 1:
                if ftype == TType.STRUCT:
                    self.userException = EDAMUserException()
                    self.userException.read(iprot)
                else:
                    iprot.skip(ftype)
            elif fid == 2:
                if ftype == TType.STRUCT:
                    self.systemException = EDAMSystemException()
                    self.systemException.read(iprot)
                else:
                    iprot.skip(ftype)
            else:
                iprot.skip(ftype)
            iprot.readFieldEnd()
        iprot.readStructEnd()

    def write(self, oprot):
        if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated:
            if self.thrift_spec is not None and fastbinary is not None:
                oprot.trans.write(fastbinary.encode_binary(self, (self.__class__,
                                                                  self.thrift_spec)))
                return
        oprot.writeStructBegin('getNoteStoreUrl_result')
        if self.success is not None:
            oprot.writeFieldBegin('success', TType.STRING, 0)
            oprot.writeString(self.success)
            oprot.writeFieldEnd()
        if self.userException is not None:
            oprot.writeFieldBegin('userException', TType.STRUCT, 1)
            self.userException.write(oprot)
            oprot.writeFieldEnd()
        if self.systemException is not None:
            oprot.writeFieldBegin('systemException', TType.STRUCT, 2)
            self.systemException.write(oprot)
            oprot.writeFieldEnd()
        oprot.writeFieldStop()
        oprot.writeStructEnd()

    def validate(self):
        return

    def __repr__(self):
        L = ['%s=%r' % (key, value)
             for key, value in self.__dict__.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)


class CustomClient(UserStore.Client):
    '''
    Getting from old version API
    '''

    def getNoteStoreUrl(self, authenticationToken):
        """
        Returns the URL that should be used to talk to the NoteStore for the
        account represented by the provided authenticationToken.
        This method isn't needed by most clients, who can retrieve the correct
        NoteStore URL from the AuthenticationResult returned from the authenticate
        or refreshAuthentication calls. This method is typically only needed
        to look up the correct URL for a long-lived session token (e.g. for an
        OAuth web service).

        Parameters:
         - authenticationToken
        """
        self.send_getNoteStoreUrl(authenticationToken)
        return self.recv_getNoteStoreUrl()

    def send_getNoteStoreUrl(self, authenticationToken):
        self._oprot.writeMessageBegin('getNoteStoreUrl',
                                      TMessageType.CALL,
                                      self._seqid)
        args = getNoteStoreUrl_args()
        args.authenticationToken = authenticationToken
        args.write(self._oprot)
        self._oprot.writeMessageEnd()
        self._oprot.trans.flush()

    def recv_getNoteStoreUrl(self, ):
        (fname, mtype, rseqid) = self._iprot.readMessageBegin()
        if mtype == TMessageType.EXCEPTION:
            x = UserStore.TApplicationException()
            x.read(self._iprot)
            self._iprot.readMessageEnd()
            raise x
        result = getNoteStoreUrl_result()
        result.read(self._iprot)
        self._iprot.readMessageEnd()
        if result.success is not None:
            return result.success
        if result.userException is not None:
            raise result.userException
        if result.systemException is not None:
            raise result.systemException
        raise UserStore.TApplicationException(
            UserStore.TApplicationException.MISSING_RESULT,
            "getNoteStoreUrl failed: unknown result"
        )


GUserStore = UserStore
GUserStore.Client = CustomClient
