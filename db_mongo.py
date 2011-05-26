"""
The MongoDB database has the following structure:

  - code table
     - device -- the device id for the process.  This is -1 if no device has been assigned yet.
     - input -- the code to execute.
  - messages: a series of messages in ipython format
  - ipython: a table to keep track of ipython ports for tab completion.  Usable when there is a single long-running ipython dedicated session for each computation.

"""

import db
import pymongo.objectid
from pymongo.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
class DB(db.DB):
    def __init__(self, *args, **kwds):
        db.DB.__init__(self, *args, **kwds)
        self.c.code.ensure_index([('device', ASCENDING)])

    def create_cell(self, input):
        _id=self.c.code.insert({'input':input, 'device':-1})
        return str(_id)
    
    def new_input_message(self, msg):
        # look up device, if a device exists for the session
        # default to a device of -1 (or None would be better)
        msg['device']=-1
        print msg, type(msg)
        self.c.input_messages.insert(msg)
    
    def get_input_messages(self, device_id, limit=None):
        """
        Find the computations that haven't been started yet
        Mark them as in-progress with the device id and return the cells
        The `limit` keyword can give an upper limit on the number of cells returned
        """
        if limit is None:
            limit=0
        unassigned_messages=list(self.c.input_messages.find({'device':-1}).limit(limit))
        self.c.input_messages.update({'_id': {'$in': [i['_id'] for i in unassigned_messages]}, '$atomic':True}, {'$set': {'device': device_id}}, multi=True)
        # TODO: also get messages for sessions on my device, and flip a flag
        # in them saying that they are in-process.

        # another possibility is to just delete them out of the
        # database, so the database really is just a queue of messages
        return unassigned_messages


    def get_unevaluated_cells(self, device_id, limit=None):
        """
        Find the computations that haven't been started yet
        Mark them as in-progress with the device id and return the cells
        The `limit` keyword can give an upper limit on the number of cells returned
        """
        if limit is None:
            limit=0
        unassigned_cells=list(self.c.code.find({'device':-1}).limit(limit))
        self.c.code.update({'_id': {'$in': [i['_id'] for i in unassigned_cells]}, '$atomic':True}, {'$set': {'device': device_id}}, multi=True)
        return unassigned_cells

    def get_messages(self, id, sequence=0):
        "Get the messages since the message with sequence number ``sequence``"
        messages=list(self.c.messages.find({'parent_header.session':id,
                                            'sequence':{'$gte':sequence}}))
        #TODO: just get the fields we want instead of deleting the ones we don't want
        for m in messages:
            del m['_id']
        return messages

    def get_evaluated_cells(self, id=None):
        import pymongo
        if id is None:
            # return all evaluated cells
            return self.c.code.find({'output':{'$exists': True}, }).sort('_id', direction=DESCENDING)
        else:
            # return just the request cell if it is evaluated
            return self.c.code.find_one({'output':{'$exists': True}, '_id':ObjectId(id)})
    
    def set_output(self, id, output):
        self.c.code.update({'_id':id}, {'$set':{'output':output}})
    def add_messages(self, id, messages):
        "Add messages to the database"
        #TODO: doesn't use the id parameter; delete?
        self.c.messages.insert(messages)
    
    def set_ipython_ports(self, kernel):
        self.c.ipython.remove()
        self.c.ipython.insert({"pid":kernel[0].pid, "xreq":kernel[1], "sub":kernel[2], "rep":kernel[3]})
    
    def get_ipython_port(self, channel):
        return self.c.ipython.find().next()[channel]
