"""
Generic Database Adapter

The database is used for storing execute requests and
permalinks, as well as any extra logging required by
the web server and/or backend.
"""


class DB(object):
    """
    Abstract base class for database adaptors.
    """

    def add(self, code, language, interacts, callback):
        """
        Add an entry to the database.
        
        INPUT:
        
        - ``code`` -- a string
        
        - ``language`` -- a string
        
        - ``interacts`` -- a string
        
        - ``callback`` -- a function accepting a single argument, the identifier
          key for the entry
        """
        raise NotImplementedError

    def get(self, key, callback):
        """
        Retrieve the entry from the database matching ``key``.
        
        INPUT:
        
        - ``key`` -- a string
        
        - ``callback`` -- a function accepting three string arguments: the code,
          the language, and the interact state.
        """
        raise NotImplementedError
