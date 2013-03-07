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

    def new_exec_msg(self, code, language, callback):
        """
        Add the code (with mode ``language``) to the database.

        This function "returns" by calling the ``callback`` function with the identifier key for the
        code.  The callback function should accept a single argument.

        :arg str code: the code
        :arg str language: the language mode
        :arg function callback: a function accepting one argument: the
            unique key for the entry in the database.
        """
        raise NotImplementedError

    def get_exec_msg(self, key, callback):
        """
        Retrieve the code and language from the database
        matching a unique identifier.

        The callback function is called with two arguments, the code
        string and the language string.

        :arg str key: a unique identifying value for the
            requested message.
        :arg function callback: a function accepting two arguments,
            the code string and the language string.
        """
        raise NotImplementedError
