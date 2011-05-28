class DB(object):
    def __init__(self, c):
        self.c = c
        
    def create_cell(self, input):
        """Insert the input into the database and return a string id"""
        raise NotImplementedError
    
    def new_input_message(self, msg):
        """Make a new input request"""
        raise NotImplementedError

    def get_input_messages(self, device_id, limit=None):
        raise NotImplementedError

    def get_unevaluated_cells(self):
        raise NotImplementedError
    
    def get_evaluated_cells(self, id=None):
        raise NotImplementedError
    
    def set_output(self, id, output):
        raise NotImplementedError

    def set_ipython_ports(self, kernel):
        raise NotImplementedError

    def get_ipython_port(self, channel):
        raise NotImplementedError
