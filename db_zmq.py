import db
import zmq
from uuid import uuid4
from random import randrange
from sys import maxint
from util import log
from json import dumps

def db_method(method_name, kwarg_keys, isFS=False):
    """
    Create a member function for :class:`db_zmq.DB` or
    :class:`filestore.FileStoreZMQ` that runs a given function
    from a trusted database adaptor.

    :arg str method_name: name of the method to call in the
        trusted database adaptor
    :arg list kwarg_keys: the list of keyword arguments to use
        when calling the method
    :arg bool isFS: True if the method is a FileStore method
        (for documentation purposes)
    :returns: the created method
    :rtype: function
    """
    def f(self, hmac=None, **kwargs):
        msg={'header': {'msg_id': str(randrange(maxint))},
             'msg_type': method_name,
             'content': dict([(kw,kwargs[kw]) for kw in kwarg_keys])}
        if hmac is not None:
            msg_str=dumps(msg)
            hmac.update(msg_str)
            self.socket.send_multipart([msg_str,hmac.digest()])
        else:
            self.socket.send_json(msg)
        # wait for output back
        output=self.socket.recv_pyobj()
        return output
    f.__doc__="""
        Created with :func:`~db_zmq.db_method`.

        See :meth:`%s.%s`

        :arg hmac: If not ``None``, this object will be updated using
            the string of the message, and the resulting digest will
            be sent to the trusted device along with the message.
        :type hmac: :mod:`hmac` object
        """%("FileStore" if isFS else "db.DB", method_name)
    return f

class DB(db.DB):
    u"""
    A database adaptor that uses \xd8MQ to access the methods of a
    DB adaptor running on a trusted account. The trusted DB adaptor
    has access to the database itself, but this adaptor can only use
    the subset of the database methods that are safe for untrusted
    access.

    :arg str address: the URL (with port number) to which to connect
        a \xd8MQ REQ socket; the REP socket on the other end should be
        bound by a trusted process.
    """
    def __init__(self, address):
        self.address=address
        self._req=None
    
    @property
    def socket(self):
        """
        The ``socket`` property is automatically initialized the first
        time it is called. We do this since we shouldn't create a
        context in a parent process. Instead, we'll wait until we
        actually start using the DB API to create a context. If you
        use the same class in a child process, you should first call
        the :meth:`new_context` method.
        """
        if self._req is None:
            self.new_context()
        return self._req

    def new_context(self):
        """
        Reconnect to the database. This function should be
        called before the first database access in each new process.
        """
        self._context=zmq.Context()
        self._req=self._context.socket(zmq.REQ)
        self._req.connect(self.address)
        log("ZMQ connecting to %s"%self.address)

    def add_messages(self, messages, hmacs=None, id=None):
        """
        See :meth:`db.DB.add_messages`
        """
        new=[]
        for m in messages:
            s=dumps(m)
            session=m['parent_header']['session']
            if session in hmacs:
                hmacs[session].update(s)
                d=hmacs[session].hexdigest()
            else:
                d=None
            new.append((s,d))
            # Possible TODO: send the HMAC digest of the session after
            # it is updated with the messages, instead of sending a new
            # digest for each individual message
        db_method('add_messages',['messages'])(self, messages=new)

    new_input_message = db_method('new_input_message', ['msg'])
    get_input_messages = db_method('get_input_messages', ['device', 'limit'])
    create_secret = db_method('create_secret', ['session'])
    close_session = db_method('close_session', ['device', 'session'])
    get_messages = db_method('get_messages', ['id','sequence'])
    register_device = db_method('register_device',['device', 'account', 'workers', 'pgid'])
