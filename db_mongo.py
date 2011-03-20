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
    
    def get_unevaluated_cells(self, device_id, limit=None):
        """
        Find the cells not in progress
        Mark them as in-progress with the device id and return the cells
        The `limit` keyword can give an upper limit on the number of cells returned
        """
        if limit is None:
            limit=0
        unassigned_cells=list(self.c.code.find({'device':-1}).limit(limit))
        self.c.code.update({'_id': {'$in': [i['_id'] for i in unassigned_cells]}, '$atomic':True}, {'$set': {'device': device_id}}, multi=True)
        return unassigned_cells
    
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
    
