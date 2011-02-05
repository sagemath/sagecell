class DB(object):
    def __init__(self, c):
        self.c = c
        
    def create_cell(self, input):
        """Insert the input into the database and return a string id"""
        raise NotImplementedError
    
    def get_unevaluated_cells(self):
        raise NotImplementedError
    
    def get_evaluated_cells(self):
        raise NotImplementedError
    
    def set_output(self, id, output):
        raise NotImplementedError

