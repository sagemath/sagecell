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
from util import log

class DB(db.DB):
    def __init__(self, *args, **kwds):
        db.DB.__init__(self, *args, **kwds)
        self.c.code.ensure_index([('device', ASCENDING)])

    def new_input_message(self, msg):
        # look up device; None means a device has not yet been assigned
        doc=self.c.sessions.find_one({'session':msg['header']['session']}, 
                                        {'device': 1})
        if doc is None:
            msg['device']=None
        else:
            msg['device']=doc['device']
 
        msg['evaluated']=False
        log("%s %s"%(msg,type(msg)))
        self.c.input_messages.insert(msg)
    
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
        device_messages=list(self.c.input_messages.find({'device':device, 'evaluated':False }))
        if len(device_messages)>0:
            self.c.input_messages.update({'_id':{'$in': [i['_id'] for i in device_messages]},
                                          '$atomic':True},
                                         {'$set': {'evaluated':True}}, multi=True)

        # if limit is None, do the query without limit
        # if the limit is >=1, do the query with the limit
        # otherwise, don't do the query.

        if limit is not None and limit<1:
            unassigned_messages=[]
        else:
            q=self.c.input_messages.find({'device':None,
                                          'evaluated':False})
            if limit is not None:
                q=q.limit(limit)
            
            unassigned_messages=list(q)
            if len(unassigned_messages)>0:
                self.c.input_messages.update({'_id': {'$in': [i['_id'] for i in unassigned_messages]}, 
                                              '$atomic':True}, 
                                             {'$set': {'device': device, 'evaluated':True}}, multi=True)
                self.c.sessions.insert([{'session':m['header']['session'], 'device':device} 
                                        for m in unassigned_messages])
                log("DEVICE %s took SESSIONS %s"%(device,
                                                    [m['header']['session']
                                                     for m in unassigned_messages]))
        return device_messages+unassigned_messages

    def close_session(self, device, session):
        """
        Delete a session<->device mapping.
        """
        self.c.sessions.remove({'session':session, 'device':device})    

    def get_messages(self, id, sequence=0):
        "Get the messages since the message with sequence number ``sequence``"
        messages=list(self.c.messages.find({'parent_header.session':id,
                                            'sequence':{'$gte':sequence}}))
        #TODO: just get the fields we want instead of deleting the ones we don't want
        for m in messages:
            del m['_id']
        return messages

    def add_messages(self, id, messages):
        "Add messages to the database"
        #TODO: doesn't use the id parameter; delete?
        self.c.messages.insert(messages)
        log("INSERTED: %s"%('\n'.join(str(m) for m in messages),))
    
    def set_ipython_ports(self, kernel):
        self.c.ipython.remove()
        self.c.ipython.insert({"pid":kernel[0].pid, "xreq":kernel[1], "sub":kernel[2], "rep":kernel[3]})
    
    def get_ipython_port(self, channel):
        return self.c.ipython.find().next()[channel]



    def get_evaluated_cells(self, id=None):
        "DEPRECATED"
        import pymongo
        if id is None:
            # return all evaluated cells
            return self.c.code.find({'output':{'$exists': True}, }).sort('_id', direction=DESCENDING)
        else:
            # return just the request cell if it is evaluated
            return self.c.code.find_one({'output':{'$exists': True}, '_id':ObjectId(id)})
    
    def set_output(self, id, output):
        "DEPRECATED"
        self.c.code.update({'_id':id}, {'$set':{'output':output}})
    def create_cell(self, input):
        "DEPRECATED"
        _id=self.c.code.insert({'input':input, 'device':-1})
        return str(_id)
    
    def get_unevaluated_cells(self, device_id, limit=None):
        """
        DEPRECATED

        Find the computations that haven't been started yet
        Mark them as in-progress with the device id and return the cells
        The `limit` keyword can give an upper limit on the number of cells returned
        """
        if limit is None:
            limit=0
        unassigned_cells=list(self.c.code.find({'device':-1}).limit(limit))
        self.c.code.update({'_id': {'$in': [i['_id'] for i in unassigned_cells]}, '$atomic':True}, {'$set': {'device': device_id}}, multi=True)
        return unassigned_cells

    valid_untrusted_methods=('get_input_messages', 'close_session', 'add_messages')
