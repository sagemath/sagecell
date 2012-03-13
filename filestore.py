from util import log

class FileStore(object):
    """
    An object that abstracts a filesystem
    """
    def __init__(self):
        raise NotImplementedError

    def new_file(self, **kwargs):
        """
        Return a file handle for a new write-only file with the
        given properties. If the file already exists, it will 
        overwritten.

        :arg \*\*kwargs: the properties of the new file (one should be
            ``filename="[filename]"``)
        :returns: an open file handle for the new file
        :rtype: file handle
        """
        raise NotImplementedError

    def delete_files(self, **kwargs):
        """
        Delete every file in the filestore whose properties match
        the keyword arguments.

        :arg \*\*kwargs: all files whose MongoDB properties match these
             will be deleted
        """
        raise NotImplementedError

    def get_file(self, **kwargs):
        """
        Return a read-only file handle for a given file
        with the properties given by the keyword arguments.
        If the file does not exist, return ``None``.

        :arg \*\*kwargs: the properties of the desired file
        :returns: the opened file, or ``None`` if no file exists
        :rtype: file handle
        """
        raise NotImplementedError

    def create_file(self, file_handle, **kwargs):
        """
        Copy an existing file into the filestore.

        :arg file file_handle: a file handle open for reading
        :arg \*\*kwargs: labels for the new file (one shoud be
            ``filename="[filename]"``)
        """
        raise NotImplementedError

    def copy_file(self, file_handle, **kwargs):
        """Copy a file from the filestore into another file.

        :arg file file_handle: a file handle open for writing
        :arg \*\*kwargs: labels to identify the file to copy
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
    
from gridfs import GridFS
import pymongo
from pymongo.objectid import ObjectId

try:
    from sagecell_config import mongo_config
except ImportError:
    # we may not be able to import sagecell_config if we are untrusted
    mongo_config=None

DEBUG = True

def Debugger(func):
    if DEBUG:
        def decorated(*args, **kwargs):
            print "****************Entering ",func.func_name
            print "    args ",args, kwargs
            ret = func(*args, **kwargs)
            print ret
            return ret
        return decorated
    else:
        return func

class FileStoreMongo(FileStore):
    """
    Filestore database using GridFS (see :mod:`gridfs`)

    :arg pymongo.database.Database connection: MongoDB database object
    """

    def __init__(self, connection):
        self._conn=connection
        self.new_context()
        self._fs=GridFS(self.database)

    def new_file(self, **kwargs):
        """
        See :meth:`FileStore.new_file`

        :rtype: :class:`gridfs.grid_file.GridIn`
        """
        self.delete_files(**kwargs)
        return self._fs.new_file(**kwargs)

    def delete_files(self, **kwargs):
        """
        See :meth:`FileStore.delete_files`
        """
        while self._fs.exists(kwargs):
            self._fs.delete(self._fs.get_last_version(**kwargs)._id)

    def get_file(self, **kwargs):
        """
        See :meth:`FileStore.get_file`

        :rtype: :class:`gridfs.grid_file.GridOut`
        """
        if self._fs.exists(kwargs):
            return self._fs.get(self._fs.get_last_version(**kwargs)._id)
        else:
            return None
    
    def create_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.create_file`
        """
        with self.new_file(**kwargs) as f:
            f.write(file_handle.read())

    def copy_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.copy_file`
        """
        file_handle.write(self.get_file(**kwargs).read())

    def new_context(self):
        """
        Reconnect to the filestore. This function should be
        called before the first filestore access in each new process.
        """
        self.database=pymongo.database.Database(self._conn, mongo_config['mongo_db'])
        uri=mongo_config['mongo_uri']
        if '@' in uri:
            # strip off optional mongodb:// part
            if uri.startswith('mongodb://'):
                uri=uri[len('mongodb://'):]
            result=self.database.authenticate(uri[:uri.index(':')],uri[uri.index(':')+1:uri.index('@')])
            if result==0:
                raise Exception("MongoDB authentication problem")

    valid_untrusted_methods=()


class FileStoreFilesystem(FileStore):
    """
    Filestore using the file system

    :arg dir: A directory in which to store files
    """
    def __init__(self, dir):
        self._dir = dir

    def _filename(_id, filename):
        return os.path.join(self._dir, '%s-%s'%(_id, filename))
    
    def new_file(self, _id, filename):
        """
        See :meth:`FileStore.new_file`
        """
        return open(self._filename(_id, filename), 'w')

    def delete_files(self, _id, filename):
        """
        See :meth:`FileStore.delete_files`
        """
        os.path.remove(self._filename(_id, filename))

    def get_file(self, _id, filename):
        """
        See :meth:`FileStore.get_file`
        """
        f=self._filename(_id, filename)
        if os.file.exists(f):
            return open(f, 'r')
        else:
            return None
    
    def create_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.create_file`
        """
        with self.new_file(**kwargs) as f:
            f.write(file_handle.read())

    def copy_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.copy_file`
        """
        file_handle.write(self.get_file(**kwargs).read())

    def new_context(self):
        """
        Empty function
        """
        pass

    valid_untrusted_methods=()

##

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

    :arg str address: the address the database should connect with
    """

    def __init__(self, address):
        self.address=address
        self._xreq=None
    
    @property
    def socket(self):
        """
        The ``socket`` property is automatically initialized the first
        time it is called. We do this since we shouldn't create a
        context in a parent process. Instead, we'll wait until we
        actually start using the db api to create a context. If you
        use the same class in a child process, you should first call
        the :meth:`new_context` method.
        """
        if self._xreq is None:
            self.new_context()
        return self._xreq

    def new_context(self):
        u"""
        Reconnect to \xd8MQ. This function should be
        called before the first database access in each new process.
        """
        self._context=zmq.Context()
        self._xreq=self._context.socket(zmq.XREQ)
        self._xreq.connect(self.address)
        log(u"ZMQ connecting to %s"%self.address)

    def create_file(self, file_handle, hmac, **kwargs):
        """
        See :meth:`FileStore.create_file`

        :arg hmac: an object to be updated with the contents
            of the message to be sent
        :type hmac: :mod:`hmac` object
        """
        # Use mmap if the filesize is larger than 1MiB;
        # otherwise just copy the string to memory before sending it
        if fstat(file_handle.fileno()).st_size>2**20:
            f=mmap.mmap(file_handle.fileno(),0,access=mmap.ACCESS_READ)
        else:
            f=file_handle.read()
        msg_str=dumps({'msg_type':'create_file',"header":str(uuid4()),
                       'content':kwargs})
        log("Sending: msg_str: %r, old_digest: %r"%(msg_str, hmac.digest()))
        hmac.update(msg_str)
        log("New digest: %r"%hmac.digest())
        message=[msg_str, hmac.digest(), f]
        self.socket.send_multipart(message,copy=False,track=True).wait()
        self.socket.recv()

    def copy_file(self, file_handle, hmac, **kwargs):
        """
        See :meth:`FileStore.copy_file`

        :arg hmac: an object to be updated with the contents
            of the message to be sent
        :type hmac: :mod:`hmac` object
        """
        msg_str=dumps({'msg_type':'copy_file','content':kwargs})
        hmac.update(msg_str)
        self.socket.send_multipart([msg_str, hmac.digest()])
        file_handle.write(self.socket.recv())

    create_secret=db_method('create_secret',['session'], True)
    new_file=db_method('new_file',['cell_id','filename'], True)
    delete_files=db_method('delete_files',['cell_id','filename'], True)
    get_file=db_method('get_file',['cell_id','filename'], True)
