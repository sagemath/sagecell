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
class FileStoreMongo(FileStore):
    
    def __init__(self, connection):
        self._conn=connection
        self._fs=GridFS(connection)

    def new_file(self, cell_id, filename):
        return self._fs.new_file(filename=filename, cell_id=cell_id)

    def delete_cell_files(self, cell_id):
        c=self.conn.find({'cell_id':cell_id}, ['_id'])
        for _id in c:
            self._fs.delete(_id)

    def get_file(self, cell_id, filename):
        _id=self._conn.find_one({'cell_id':cell_id, 'filename':filename}, ['_id'])
        # find id of file with cell_id and filename
        return self._fs.get(_id)
