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

    async def add(self, code, language, interacts):
        """
        Add an entry to the database.
        
        INPUT:
        
        - ``code`` -- a string
        
        - ``language`` -- a string
        
        - ``interacts`` -- a string
        
        OUTPUT:
        
        - a string -- the identifier key for the entry
        """
        raise NotImplementedError

    async def get(self, key):
        """
        Retrieve the entry from the database matching ``key``.
        
        INPUT:
        
        - ``key`` -- a string
        
        OUTPUT:
        
        - a tuple of three strings: the code, the language, the interact state.
        """
        raise NotImplementedError
