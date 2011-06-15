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
import pymongo.objectid
from pymongo.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from singlecell_config import mongo_config
from util import log

class DB(db.DB):
    def __init__(self, *args, **kwds):
        db.DB.__init__(self, *args, **kwds)
        self.new_context()
        self.database.sessions.ensure_index([('session', ASCENDING)])
        self.database.input_messages.ensure_index([('device', ASCENDING)])
        self.database.input_messages.ensure_index([('evaluated',ASCENDING)])
        self.database.messages.ensure_index([('parent_header.session', ASCENDING)])

    def new_input_message(self, msg):
        # look up device; None means a device has not yet been assigned
        doc=self.database.sessions.find_one({'session':msg['header']['session']}, 
                                        {'device': 1})
        if doc is None:
            msg['device']=None
        else:
            msg['device']=doc['device']
 
        msg['evaluated']=False
        log("%s %s"%(msg,type(msg)))
        self.database.input_messages.insert(msg)
    
    def get_input_messages(self, device, limit=None):
        """
        Find the computations that haven't been started yet
        Mark them as in-progress with the device id and return the cells
        The `limit` keyword can give an upper limit on the number of unassigned sessions returned

        The database also stores a list of sessions for each device.
        Currently, we rely on each message having a device attribute
        that is set, if possible, when the message is created. Another
        possibility is to just have the device query the sessions table to
        return the sessions that are currently active. I'm not sure which is
        faster.
        """
        
        # find the sessions for this device
        device_messages=list(self.database.input_messages.find({'device':device, 'evaluated':False }))
        if len(device_messages)>0:
            self.database.input_messages.update({'_id':{'$in': [i['_id'] for i in device_messages]},
                                          '$atomic':True},
                                         {'$set': {'evaluated':True}}, multi=True)

        # if limit is 0, don't do the query (just return empty list)
        # if limit is None or negative, do the query without limit
        # otherwise do the query with the specified limit

        if limit==0:
            unassigned_messages=[]
        else:
            q=self.database.input_messages.find({'device':None,
                                          'evaluated':False})
            if limit is not None and limit>=0:
                q=q.limit(limit)
            
            unassigned_messages=list(q)
            if len(unassigned_messages)>0:
                self.database.input_messages.update({'_id': {'$in': [i['_id'] for i in unassigned_messages]}, 
                                              '$atomic':True}, 
                                             {'$set': {'device': device, 'evaluated':True}}, multi=True)
                self.database.sessions.insert([{'session':m['header']['session'], 'device':device} 
                                        for m in unassigned_messages])
                log("DEVICE %s took SESSIONS %s"%(device,
                                                    [m['header']['session']
                                                     for m in unassigned_messages]))
        return device_messages+unassigned_messages

    def close_session(self, device, session):
        u"""
        Delete a session\u2194device mapping.
        """
        self.database.sessions.remove({'session':session, 'device':device})    

    def get_messages(self, id, sequence=0):
        "Get the messages since the message with sequence number ``sequence``"
        messages=list(self.database.messages.find({'parent_header.session':id,
                                            'sequence':{'$gte':sequence}}))
        #TODO: just get the fields we want instead of deleting the ones we don't want
        for m in messages:
            del m['_id']
        return messages

    def add_messages(self, id, messages):
        "Add messages to the database"
        #TODO: doesn't use the id parameter; delete?
        self.database.messages.insert(messages)
        log("INSERTED: %s"%('\n'.join(str(m) for m in messages),))
    

    def register_device(self, device, account, workers, pgid):
        """
        Register a device with the database

        We store the pgid so that we can later kill the device and all
        subprocesses by sshing into the account (if set) and doing::

            import os, signal
            os.kill(pgid, signal.SIGKILL) #or signal.SIGTERM to be nicer about it
        """
        doc={"device":device, "account":account, "workers": workers, "pgid":pgid}
        self.database.device.insert(doc)
        log("REGISTERED DEVICE: %s"%doc)

    def delete_device(self, device):
        """
        Delete a device record from the database

        """
        self.database.device.remove({'device': device})

    def get_devices(self):
        """
        Return a list of currently registered devices.
        """
        return list(self.database.device.find())

    def set_ipython_ports(self, kernel):
        self.database.ipython.remove()
        self.database.ipython.insert({"pid":kernel[0].pid, "xreq":kernel[1], "sub":kernel[2], "rep":kernel[3]})
    
    def get_ipython_port(self, channel):
        return self.database.ipython.find().next()[channel]

    def new_context(self):
        self.database=pymongo.database.Database(self.c, mongo_config['mongo_db'])
        uri=mongo_config['mongo_uri']
        if '@' in uri:
            print uri[:uri.index(':')],uri[uri.index(':')+1:uri.index('@')]
            # strip off optional mongodb:// part
            if uri.startswith('mongodb://'):
                uri=uri[len('mongodb://'):]
            result=self.database.authenticate(uri[:uri.index(':')],uri[uri.index(':')+1:uri.index('@')])
            if result==0:
                raise UserError("Authentication problem")

    valid_untrusted_methods=('get_input_messages', 'close_session', 'add_messages')
