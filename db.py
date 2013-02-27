"""
Generic Database Adapter
------------------------

The database is used for storing execute requests and
permalinks, as well as any extra logging required by
the web server and/or backend.

Various classes can extend this :class:`DB` class in
order to allow for a choice of the database used.
"""

class DB(object):
    """
    Abstract base class for database adaptors.
    """

    def __init__(self):
        raise NotImplementedError

    def new_exec_msg(self, msg):
        """
        Add an exec_request message to the database to be
        retrieved by :meth:`get_exec_msg`.

        :arg dict msg: a JSON-compatible message containing
            code to be executed by the kernel.
        """
        raise NotImplementedError

    def get_exec_msg(self, ident):
        """
        Retrieve an exec_request message from the database
        matching a unique identifier.

        :arg str ident: a unique identifying value for the
            requested message.
        :returns: (string of the code, string of the language)
        :rtype: tuple of str
        """
        raise NotImplementedError
