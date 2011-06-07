class DB(object):
    """
    Base class for database adaptors
    """

    def __init__(self, c):
        self.c = c
        
    def create_cell(self, input):
        """
        Insert code into the database to be executed

        :arg input: code to insert
        :type input: str
        :returns: an ID for the code
        :rtype: str
        """
        raise NotImplementedError
    
    def new_input_message(self, msg):
        """
        Make a new input request
        """
        raise NotImplementedError

    def get_input_messages(self, device_id, limit=None):
        """
        Find the computations that haven't been started yet,
        mark them as in-progress with the device ID and return the cells.

        The database also stores a list of sessions for each device.
        Currently, we rely on each message having a device attribute
        that is set, if possible, when the message is created. Another
        possibility is to just have the device query the sessions table to
        return the sessions that are currently active. I'm not sure which is
        faster.

        :arg device_id: the ID of the device
        :type device_id: str
        :arg limit: the maximum number of computations to retrieve
        :type limit: int
        :returns: a list of cells
        """
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
