"""
MongoDB Database Adapter
------------------------

The MongoDB database has the following collections:

    - ``device``: information on each device process
       - ``device`` (str) - device id
       - ``account`` (str) - the ssh account for the device
       - ``workers`` (int) - the number of workers
       - ``pgid`` (int) - the parent group id of the device (used to shutdown the device)
    
    - ``input_messages``: the code to execute

        - ``evaluated`` (bool, indexed) - whether or not a message has been evaluated
        - ``device`` (str, indexed) -  the ID of the device to which this message has
          been assigned; ``None`` if it has not yet been assigned
          to a device
        - ``shortened`` (str, indexed) - a short identifier for the input, for permalinks
        - ``timestamp`` (datetime) - the timestamp of the input
   

    - ``messages``: a series of messages in IPython format
        - index on parent_header.session
        - sequence

    - ``ipython``: a table to keep track of IPython ports for tab
      completion (usable when there is a single long-running dedicated
      IPython session for each computation.)
    - ``sessions``: a table listing which device is assigned to each session
        - session (indexed str) - session
        - device
    
"""

import db
import pymongo
from pymongo import ASCENDING, DESCENDING
try:
    from sagecell_config import mongo_config
except ImportError:
    from sagecell_config_default import mongo_config

from util import log
import uuid

class DB(db.DB):
    """
    MongoDB database adaptor

    :arg pymongo.Connection c: the PyMongo Connection object
        for the database
    """

    def __init__(self, c):
        self.c=c
        self.new_context()
        self.database.sessions.ensure_index([('session', ASCENDING)])
        self.database.input_messages.ensure_index([('device', ASCENDING)])
        self.database.input_messages.ensure_index([('evaluated',ASCENDING)])
        self.database.input_messages.ensure_index([('shortened',ASCENDING)])
        self.database.messages.ensure_index([('parent_header.session', ASCENDING)])

    def new_input_message(self, msg):
        # look up device; None means a device has not yet been assigned
        # Note that this makes it easy for an attacker to inject messages into a session
        # if they can snoop the session ID
        doc=self.database.sessions.find_one({'session':msg['header']['session']}, 
                                        {'device': 1})
        if doc is None:
            msg['device']=None
        else:
            msg['device']=doc['device']
 
        msg['evaluated']=False
        import datetime
        msg['timestamp']=datetime.datetime.utcnow()
        self.database.input_messages.insert(msg)

    def get_input_message_by_shortened(self, shortened):
        """
        See :meth:`db.DB.get_input_message_by_shortened`
        """
        doc=self.database.input_messages.find_one({'shortened': shortened}, {'content.code': 1})
        if doc is not None:
            return doc['content']['code']
        else:
            return ""

    def get_input_messages(self, device, limit=None):
        """
        See :meth:`db.DB.get_input_messages`
        """
        # find the sessions for this device
        device_messages=[]
        while True:
            msg = self.database.input_messages.find_and_modify({'device':device, 'evaluated':False },
                                                               {'$set': {'evaluated':True}})
            if msg is None:
                break
            else:
                device_messages.append(msg)


        # if limit is 0, don't do the query (just return empty list)
        # if limit is None or negative, do the query without limit
        # otherwise do the query with the specified limit
        unassigned_messages=[]

        if limit==0:
            pass # do nothing
        elif limit is None or limit<0:
            while True:
                msg = self.database.input_messages.find_and_modify({'device':None, 'evaluated':False },
                                                                   {'$set': {'device': device, 'evaluated':True}})
                if msg is None:
                    break
                else:
                    unassigned_messages.append(msg)
        else:
            while limit>0:
                msg = self.database.input_messages.find_and_modify({'device':None, 'evaluated':False },
                                                                   {'$set': {'device': device, 'evaluated':True}})
                if msg is None:
                    break
                else:
                    unassigned_messages.append(msg)
                    limit -= 1
        if len(unassigned_messages)>0:
            self.database.sessions.insert([{'session':m['header']['session'], 'device':device} 
                                           for m in unassigned_messages])
            log("DEVICE %s took SESSIONS %s"%(device, [m['header']['session'] for m in unassigned_messages]))

        return device_messages+unassigned_messages

    def close_session(self, device, session):
        """
        See :meth:`db.DB.close_session`
        """
        self.database.sessions.remove({'session':session, 'device':device})

    def get_messages(self, session, sequence=0):
        """
        See :meth:`db.DB.get_messages`
        """
        messages=list(self.database.messages.find({'parent_header.session':session,
                                            'sequence':{'$gte':sequence}}))
        #TODO: just get the fields we want instead of deleting the ones we don't want
        for m in messages:
            del m['_id']
        return messages

    def add_messages(self, messages):
        """
        See :meth:`db.DB.add_messages`
        """
        # We have to insert messages one at a time, so that an error doesn't
        # cause the remaining messages in the list to be ignored
        success = []
        for m in messages:
            try:
                self.database.messages.insert(m)
                success.append(m)
            except Exception as e:
                self.database.messages.insert({
                      "content": {"status": "error",
                                  "ename": "", "evalue": "",
                                  "traceback": ["\x1b[1;31mError: \x1b[1;30m%s" % e.message]},
                      "header": m["header"],
                      "parent_header": m["parent_header"],
                      "msg_type": "execute_reply",
                      "output_block": None,
                      "sequence": m["sequence"]})
        log("INSERTED: %s"%('\n'.join(str(m)[:1000] for m in success),))
        if len(success) < len(messages):
            log("FAILED TO INSERT %d message(s)" % (len(messages) - len(success)))

    def purge_output(self):
        """
        Purges all output (files and output messages) in the database.
        Be careful calling this function!
        """
        self.database.messages.remove(safe=True)
        self.database.fs.files.remove(safe=True)
        self.database.fs.chunks.remove(safe=True)

    def register_device(self, device, account, workers, pgid):
        """
        See :meth:`db.DB.register_device`
        """
        doc={"device":device, "account":account, "workers": workers, "pgid":pgid}
        self.database.device.insert(doc)
        log("REGISTERED DEVICE: %s"%doc)

    def delete_device(self, device):
        """
        See :meth:`db.DB.delete_device`
        """
        self.database.device.remove({'device': device})

    def get_devices(self):
        """
        See :meth:`db.DB.get_devices`
        """
        return list(self.database.device.find())

    def set_ipython_ports(self, kernel):
        """
        See :meth:`db.DB.set_ipython_ports`
        """
        self.database.ipython.remove()
        self.database.ipython.insert({"pid":kernel[0].pid, "xreq":kernel[1], "sub":kernel[2], "rep":kernel[3]})
    
    def get_ipython_port(self, channel):
        """
        See :meth:`db.DB.get_ipython_port`
        """
        return self.database.ipython.find().next()[channel]

    def new_context(self):
        """
        See :meth:`db.DB.new_context`
        """
        self.database=pymongo.database.Database(self.c, mongo_config['mongo_db'])
        uri=mongo_config['mongo_uri']
        if '@' in uri:
            # strip off optional mongodb:// part
            if uri.startswith('mongodb://'):
                uri=uri[len('mongodb://'):]
            result=self.database.authenticate(uri[:uri.index(':')],uri[uri.index(':')+1:uri.index('@')])
            if result==0:
                raise Exception("MongoDB authentication problem")

    def new_context_copy(self):
        return type(self)(self.c)

    valid_untrusted_methods=('get_input_messages', 'close_session', 'add_messages')
