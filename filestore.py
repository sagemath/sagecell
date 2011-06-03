"""
This is a base class for File Stores

"""

class FileStore(object):

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
    
    def __init__(self, connection):
        self._conn=connection
        self._fs=GridFS(connection)

    def new_file(self, cell_id, filename):
        self.delete_files(cell_id=cell_id, filename=filename)
        return self._fs.new_file(filename=filename, cell_id=cell_id)

    def delete_files(self, **kwargs):
        while self._fs.exists(kwargs):
            self._fs.delete(self._fs.get_last_version(**kwargs)._id)

    def get_file(self, **kwargs):
        if self._fs.exists(kwargs):
            return self._fs.get(self._fs.get_last_version(**kwargs)._id)
        else:
            return None
    
    def create_file(self, file_handle, **kwargs):
        with self.new_file(**kwargs) as f:
            f.write(file_handle.read())

import zmq
from db_zmq import db_method
from uuid import uuid4
from json import dumps
class FileStoreZMQ(FileStoreMongo):
    def __init__(self, *args, **kwds):
        self.context=kwds['context']
        self.c=self.context.socket(zmq.REQ)
        self.c.connect(kwds['socket'])
    def create_file(self, file_handle, **kwargs):
        message=[dumps({'msg_type':'create_file',"header":str(uuid4()),
                        'content':kwargs}), file_handle.read()]
        self.c.send_multipart(message,copy=False,track=True).wait()
        self.c.recv()

    new_file=db_method('new_file',['cell_id','filename'])
    delete_cell_files=db_method('delete_cell_files',['cell_id'])
    get_file=db_method('get_file',['cell_id','filename'])
