"""
The MongoDB database has the following structure:

  - code table
     - device -- the device id for the process.  This is -1 if no device has been assigned yet.
     - input -- the code to execute.
  - messages: a series of messages in ipython format
  - ipython: a table to keep track of ipython ports for tab completion.  Usable when there is a single long-running ipython dedicated session for each computation.
  - sessions: a table listing, for each session, which device is assigned to the session

"""

import db
import zmq
from uuid import uuid4
from random import randrange
from sys import maxint
from util import log

def db_method(method_name, kwarg_keys):
    def f(self, **kwargs):
        msg={'header': {'msg_id': str(randrange(maxint))},
             'msg_type': method_name,
             'content': dict([(kw,kwargs[kw]) for kw in kwarg_keys])}
        self.req.send_json(msg)
        # wait for output back
        output=self.req.recv_pyobj()
        return output
    return f

class DB(db.DB):
    def __init__(self, *args, **kwargs):
        """
        ``address`` is a kwarg, which should be the address the database should connect with
        """
        self.address=kwargs['address']
        self._req=None
    
    @property
    def req(self):
        """
        The ``req`` property is automatically initialized the first
        time it is called. We do this since we shouldn't create a
        context in a parent process. Instead, we'll wait until we
        actually start using the db api to create a context. If you
        use the same class in a child process, you should first call
        the :meth:`new_context` method.
        """
        if self._req is None:
            self.new_context()
        return self._req

    def new_context(self):
        self._context=zmq.Context()
        self._req=self._context.socket(zmq.REQ)
        self._req.connect(self.address)
        log("ZMQ connecting to %s"%self.address)
        
            
    new_input_message = db_method('new_input_message', ['msg'])
    get_input_messages = db_method('get_input_messages', ['device', 'limit'])
    close_session = db_method('close_session', ['device', 'session'])
    get_messages = db_method('get_messages', ['id','sequence'])
    add_messages = db_method('add_messages', ['id', 'messages'])
    set_device_pgid = db_method('set_device_pgid',['device', 'account', 'pgid'])
