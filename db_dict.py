
# TODO: THIS is not used yet -- right after we wrote it, we realized
# that we would also have to write a networked client/server
# interface, e.g., using xmlrpc or something.  

import db

class DB(db.DB):
    def __init__(self, c=None):
        if c is None:
            c = {}
        self.c = c
        self.c['cells'] = {'evaluated':{}, 'unevaluated':{}}
        self._id = 0
        
    def create_cell(self, input):
        self.c['cells']['unevaluated'][self._id] = input
        self._id += 1
    
    def get_unevaluated_cells(self):
        for id, input in self.c['cells']['unevaluated'].iteritems():
            yield {'_id':id, 'input':input}
    
    def get_evaluated_cells(self):
        for id, (input, output) in sorted(self.c['cells']['evaluated'].items(), reverse=True):
            yield {'_id':id, 'input':input, 'output':output}

    def set_output(self, id, output):
        cells = self.c['cells']
        cells['evaluated'][id] = (cells['unevaluated'][id], output)
        del cells['unevaluated'][id]
    
