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
        return self._fs.new_file(filename=filename, cell_id=ObjectId(cell_id))

    def delete_cell_files(self, cell_id):
        c=self.conn.find({'cell_id':ObjectId(cell_id)}, ['_id'])
        for _id in c:
            self._fs.delete(_id)

    def get_file(self, cell_id, filename):
        _id=self._conn.fs.files.find_one({'cell_id':ObjectId(cell_id), 'filename':filename},['_id'])
        return self._fs.get(_id['_id'])

import zmq
from db_zmq import db_method
class FileStoreZMQ(FileStoreMongo):
    def __init__(self, *args, **kwds):
        self.context=kwds['context']
        self.rep=self.context.socket(zmq.REP)
        self.rep.connect(kwds['socket'])
    new_file=db_method('new_file',['cell_id','filename'])
    delete_cell_files=db_method('delete_cell_files',['cell_id'])
    get_file=db_method('get_file',['cell_id','filename'])
