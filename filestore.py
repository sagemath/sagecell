from util import log

class FileStore(object):
    """
    This is a base class for File Stores
    """
    def __init__(self, connection=None):
        pass

    def new_file(self, cell_id, filename):
        """
        Return a file handle for a new file (write-only) with the given filename associated with the cell id.
        """
        pass

    def delete_cell_files(self, cell_id):
        "Delete all files associated with a cell id"
        pass

    def get_file(self, cell_id, filename):
        "Return a file handle (read-only) for a given file associated with a cell id"
        pass

    
from gridfs import GridFS
from pymongo.objectid import ObjectId
class FileStoreMongo(FileStore):
    """
    Filestore database using GridFS

    :arg connection: MongoDB database object
    :type connection: pymongo.database.Database
    """

    def __init__(self, connection):
        self._conn=connection
        self._fs=GridFS(connection)

    def new_file(self, **kwargs):
        """
        Create or recreate a file labeled with the given keyword arguments.

        :returns: an open file handle for the new file
        :rtype: gridfs.GridIn
        """
        self.delete_files(**kwargs)
        return self._fs.new_file(**kwargs)

    def delete_files(self, **kwargs):
        """
        Delete every file in the filestore labeled with the keyword arguments.
        """
        while self._fs.exists(kwargs):
            self._fs.delete(self._fs.get_last_version(**kwargs)._id)

    def get_file(self, **kwargs):
        if self._fs.exists(kwargs):
            return self._fs.get(self._fs.get_last_version(**kwargs)._id)
        else:
            return None
    
    def create_file(self, file_handle, **kwargs):
        """
        Copy an existing file into the filestore database.

        :arg file_handle: a handle to a file open for reading
        :type file_handle: file
        :arg \*\*kwargs: labels (including filename) for the new file
        """
        with self.new_file(**kwargs) as f:
            f.write(file_handle.read())

    valid_untrusted_methods=()

import zmq
from db_zmq import db_method
from uuid import uuid4
from json import dumps
from os import fstat
import mmap
class FileStoreZMQ(FileStoreMongo):
    u"""
    A connection to a filestore database over \xd8MQ.
    This can be used in the same way as a normal filestore,
    but without risk of compromising the database.

    :arg address: the address the database should connect with
    :type address: str
    """

    def __init__(self, address):
        self.address=address
        self._req=None
    
    @property
    def req(self):
        """
        The ``req`` property is automatically initialized the first
        time it is called. We do this since we shouldn't create a
        context in a parent process. Instead, we'll wait until we
        actually start using the db api to create a context. If you
        use the same class in a child process, you should first call
        the :meth:`new_context` method.
        """
        if self._req is None:
            self.new_context()
        return self._req

    def new_context(self):
        self._context=zmq.Context()
        self._req=self._context.socket(zmq.REQ)
        self._req.connect(self.address)
        log("ZMQ connecting to %s"%self.address)

    def create_file(self, file_handle, hmac, **kwargs):
        # Use mmap if the filesize is larger than 1MiB;
        # otherwise just copy the string to memory before sending it
        if fstat(file_handle.fileno()).st_size>2**20:
            f=mmap.mmap(file_handle.fileno(),0,access=mmap.ACCESS_READ)
        else:
            f=file_handle.read()
        msg_str=dumps({'msg_type':'create_file',"header":str(uuid4()),
                        'content':kwargs})
        hmac.update(msg_str)
        message=[msg_str, hmac.digest(), f]
        self.req.send_multipart(message,copy=False,track=True).wait()
        self.req.recv()

    def copy_file(self, file_handle, hmac, **kwargs):
        msg_str=dumps({'msg_type':'copy_file','content':kwargs})
        hmac.update(msg_str)
        self.req.send_multipart([msg_str, hmac.digest()])
        file_handle.write(self.req.recv())

    create_secret=db_method('create_secret',['session'])
    new_file=db_method('new_file',['cell_id','filename'])
    delete_cell_files=db_method('delete_cell_files',['cell_id'])
    get_file=db_method('get_file',['cell_id','filename'])
