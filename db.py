"""
The database is where information that needs to be accessed
by different pieces of the backend is stored. This includes
the code inside each executed cell, and the output messages
produced when the code is run.

There are several different classes that extend the
:class:`DB` class in order to allow for a choice of
the database used.
"""

class DB(object):
    """
    Abstract base class for database adaptors.
    """

    def __init__(self):
        raise NotImplementedError
        
    def new_input_message(self, msg):
        """
        Add a new computation request to the database to be retrieved
        by :meth:`get_input_messages`.

        :arg dict msg: the IPython-style message containing a new
            string of code to execute
        """
        raise NotImplementedError

    def get_input_messages(self, device, limit=None):
        """
        Find the computations that haven't been started yet,
        mark them as in-progress with the device ID and return
        the cells. The :obj:`limit` keyword can give an upper 
        on the number of unassigned sessions returned.

        The database also stores a list of sessions for each device.
        Currently, we rely on each message having a device attribute
        that is set, if possible, when the message is created. Another
        possibility is to just have the device query the sessions table to
        return the sessions that are currently active. I'm not sure which is
        faster.

        :arg str device_id: the ID of the device
        :arg int limit: the maximum number of computations to retrieve
        :returns: a list of cells
        :rtype: list
        """
        raise NotImplementedError

    def get_input_message_by_shortened(self, shortened):
        """
        Retrieve the input code for a shortened field
        
        :arg str shortened: the shortened identifier for the input message
        :returns: a string containing the input code, or the empty string if
            the shortened ID does not match any input.
        :rtype: str
        """
        raise NotImplementedError

    def add_messages(self, messages):
        """
        Add IPython-style output messages to the database.

        :arg list output: the messages to add
        """
        raise NotImplementedError

    def register_device(self, device, account, workers, pgid):
        """
        Register a device with the database

        We store the pgid so that we can later kill the device and all
        subprocesses by sshing into the account (if set) and doing::

            import os, signal
            os.kill(pgid, signal.SIGKILL) #or signal.SIGTERM to be nicer about it

        :arg str device: device ID
        :arg str account: account
        :arg int workers: number of workers
        :arg int pgid: process group ID
        """
        raise NotImplementedError

    def delete_device(self, device):
        """
        Delete a device from the database

        :arg str device: device ID
        """
        raise NotImplementedError

    def get_devices(self):
        """
        :returns: currently registered devices
        :rtype: list
        """
        raise NotImplementedError

    def get_messages(self, session, sequence=0):
        """
        Get the messages from some session, starting with
        the message with sequence number ``sequence``.

        :arg str session: the session ID
        :arg int sequence: the minimum sequence in the returned messages
        :returns: a list of IPython-style messages
        """
        raise NotImplementedError

    def close_session(self, device, session):
        u"""
        Delete a session-to-device mapping.

        :arg str device: the ID of the device
        :arg str session: the ID of the session
        """
        raise NotImplementedError

    def create_secret(self, session):
        """
        Generate a new :mod:`hmac` object and associate it
        with the session. Used only with "untrusted" database
        adaptors. (See :ref:`trusted`.)

        :arg str session: the ID of the new session
        """
        raise NotImplementedError

    def set_ipython_ports(self, kernel):
        """
        Set the ports with which an IPython kernel can communicate
        with another process. Used only with the IPython device.

        :arg tuple kernel: the ports used by the IPython kernel
        """
        raise NotImplementedError

    def get_ipython_port(self, channel):
        """
        Get a port with which an IPython kernel can communicate
        with another process. Used only with the IPython device.

        :arg str channel: IPython channel name (``"pid"``, ``"xreq"``,
            ``"sub"``, or ``"rep"``)
        :returns: port number
        :rtype: int
        """
        raise NotImplementedError

    def new_context(self):
        """
        Reconnect to the database. This function should be
        called before the first database access in each new process.
        """

    def new_context_copy(self):
        """
        Create a copy of this object for use in a single thread.

        :returns: a new database object
        :rtype: DB
        """
