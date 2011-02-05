import db

class DB(db.DB):
    def create_cell(self, input):
        _id=self.c.code.insert({'input':input})
        return str(_id)
    
    def get_unevaluated_cells(self):
        return self.c.code.find({'output':{'$exists': False}})
    
    def get_evaluated_cells(self):
        import pymongo
        return self.c.code.find({'output':{'$exists': True}}).sort('_id', direction=pymongo.DESCENDING)
    
    def set_output(self, id, output):
        self.c.code.update({'_id':id}, {'$set':{'output':output}})
    
