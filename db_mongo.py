import db
import pymongo.objectid
from pymongo.objectid import ObjectId
class DB(db.DB):
    def create_cell(self, input):
        _id=self.c.code.insert({'input':input})
        return str(_id)
    
    def get_unevaluated_cells(self):
        return self.c.code.find({'output':{'$exists': False}})
    
    def get_evaluated_cells(self, id=None):
        import pymongo
        if id is None:
            # return all evaluated cells
            return self.c.code.find({'output':{'$exists': True}, }).sort('_id', direction=pymongo.DESCENDING)
        else:
            # return just the request cell if it is evaluated
            return self.c.code.find_one({'output':{'$exists': True}, '_id':ObjectId(id)})
    
    def set_output(self, id, output):
        self.c.code.update({'_id':id}, {'$set':{'output':output}})
    
