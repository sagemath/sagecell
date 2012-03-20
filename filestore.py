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

    def new_context(self):
        """
        Reconnect to the filestore. This function should be
        called before the first filestore access in each new process.
        """

    def new_context_copy(self):
        """
        Create a copy of this object for use in a single thread.

        :returns: a new filestore object
        :rtype: FileStore
        """

try:
    from sagecell_config import mongo_config
except ImportError:
    # we may not be able to import sagecell_config if we are untrusted
    mongo_config=None

DEBUG = False

def Debugger(func):
    if DEBUG:
        def decorated(*args, **kwargs):
            print "****************Entering ",func.func_name
            print "    args ",args, kwargs
            #try:
            #    print "filename: %s"%(args[0]._filename(**kwargs),)
            #except Exception as a:
            #    print "Couldn't get filename", a
            ret = func(*args, **kwargs)
            print ret
            return ret
        return decorated
    else:
        return func

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.types import Binary
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from StringIO import StringIO

class FileStoreSQLAlchemy(FileStore):
    """
    A filestore in a SQLAlchemy database.
    
    :arg str fs_file: the SQLAlchemy URI for a database file
    """
    def __init__(self, fs_file=None):
        if fs_file is not None:
            engine = create_engine(fs_file)
            self.SQLSession = sessionmaker(bind=engine)
            FileStoreSQLAlchemy.Base.metadata.create_all(engine)
            self.new_context()

    @Debugger
    def new_file(self, session, filename, **kwargs):
        """
        See :meth:`FileStore.new_file`
        """
        self.delete_files(session, filename)
        log("FS Creating %s/%s"%(session, filename))
        return FileStoreSQLAlchemy.DBFileWriter(self, session, filename)

    @Debugger
    def delete_files(self, session=None, filename=None, **kwargs):
        """
        See :meth:`FileStore.new_file`
        """
        q = self.dbsession.query(FileStoreSQLAlchemy.StoredFile)
        if session is not None:
            q = q.filter_by(session=session)
        if filename is not None:
            q = q.filter_by(filename=filename)
        q.delete()
        self.dbsession.commit()

    @Debugger
    def get_file(self, session, filename, **kwargs):
        """
        See :meth:`FileStore.get_file`
        """
        return StringIO(self.dbsession.query(FileStoreSQLAlchemy.StoredFile.contents) \
                .filter_by(session=session, filename=filename).first().contents)

    @Debugger
    def create_file(self, file_handle, session, filename, **kwargs):
        """
        See :meth:`FileStore.create_file`
        """
        f = FileStoreSQLAlchemy.StoredFile(session=session, filename=filename)
        if type(file_handle) is FileStoreSQLAlchemy.DBFileWriter:
            contents = file_handle.getvalue()
        else:
            contents = file_handle.read()
        f.contents = contents
        self.dbsession.add(f)
        self.dbsession.commit()

    @Debugger
    def copy_file(self, file_handle, session, filename, **kwargs):
        """
        See :meth:`FileStore.copy_file`
        """
        self.dbsession.add(FileStoreSQLAlchemy.StoredFile(session=session,
                filename=filename, contents=file_handle.read()))
        self.dbsession.commit()

    @Debugger
    def new_context(self):
        """
        See :meth:`FileStore.new_context`
        """
        self.dbsession = self.SQLSession()

    @Debugger
    def new_context_copy(self):
        """
        See :meth:`FileStore.new_context_copy`
        """
        new = type(self)()
        new.SQLSession = self.SQLSession
        new.new_context()
        return new

    Base = declarative_base()
    
    class StoredFile(Base):
        """A file stored in the database"""
        __tablename__ = 'filestore'
        n = Column(Integer, primary_key=True)
        session = Column(String)
        filename = Column(String)
        contents = Column(Binary)

    class DBFileWriter(StringIO, object):
        """
        A file-like object that writes its contents to the database when it is
        closed.
        
        :arg FileStoreSQLAlchemy filestore: the filestore object to write to
        :arg str session: the ID of the session that is the source of this file
        :arg str filename: the name of the file
        """
        def __init__(self, filestore, session, filename):
            self.filestore = filestore
            self.session = session
            self.filename = filename
            super(type(self), self).__init__()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()
        def close(self):
            self.filestore.create_file(self, self.session, self.filename)
            super(type(self), self).close()

try:
    from gridfs import GridFS
    import pymongo
    from pymongo.objectid import ObjectId
except ImportError:
    pass

class FileStoreMongo(FileStore):
    """
    Filestore database using GridFS (see :mod:`gridfs`)

    :arg pymongo.database.Database connection: MongoDB database object
    """

    def __init__(self, connection):
        self._conn=connection
        self.new_context()
        self._fs=GridFS(self.database)

    def _filename(self, **kwargs):
        return {'session': kwargs.get('session', kwargs.get('cell_id', 'SESSION NOT FOUND')), 'filename': kwargs['filename']}
    @Debugger
    def new_file(self, **kwargs):
        """
        See :meth:`FileStore.new_file`

        :rtype: :class:`gridfs.grid_file.GridIn`
        """
        self.delete_files(**kwargs)
        log("FS Creating %s"%self._filename(**kwargs))
        return self._fs.new_file(**self._filename(**kwargs))

    @Debugger
    def delete_files(self, **kwargs):
        """
        See :meth:`FileStore.delete_files`
        """
        while self._fs.exists(self._filename(**kwargs)):
            self._fs.delete(self._fs.get_last_version(**self._filename(**kwargs))._id)

    @Debugger
    def get_file(self, **kwargs):
        """
        See :meth:`FileStore.get_file`

        :rtype: :class:`gridfs.grid_file.GridOut`
        """
        if self._fs.exists(self._filename(**kwargs)):
            return self._fs.get(self._fs.get_last_version(**self._filename(**kwargs))._id)
        else:
            return None
    
    @Debugger
    def create_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.create_file`
        """
        with self.new_file(**kwargs) as f:
            f.write(file_handle.read())

    @Debugger
    def copy_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.copy_file`
        """
        file_handle.write(self.get_file(**kwargs).read())

    @Debugger
    def new_context(self):
        """
        See :meth:`FileStore.new_context`
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

    @Debugger
    def new_context_copy(self):
        """
        See :meth:`FileStore.new_context_copy`
        """
        return type(self)(self._conn)

    valid_untrusted_methods=()

from flask import safe_join
import os

class FileStoreFilesystem(FileStore):
    """
    Filestore using the file system

    The levels parameter controls how the session is split up to give
    subdirectories.  For example, if levels=4, then session
    0c490701-b1b0-40b8-88ea-70b61a580cf2 files are stored in
    subdirectory ``0/c/4/9/0c490701-b1b0-40b8-88ea-70b61a580cf2``.
    This prevents having too many directories in the root directory.

    :arg dir: A directory in which to store files
    :arg levels: The number of levels to use for splitting up session directories
    """
    def __init__(self, dir, levels=0):
        self._dir = dir
        self._levels=levels

    def _filename(self, **kwargs):
        if 'session' in kwargs:
            session=kwargs['session']
        elif 'cell_id' in kwargs:
            session = kwargs['cell_id']
        else:
            session = "SESSION_NOT_FOUND"
        session_subdir = list(str(session)[:self._levels])+[str(session)]
        # Use Flask's safe_join to make sure we don't overwrite something crucial
        session_dir = safe_join(self._dir, os.path.join(*session_subdir))
        if not os.path.isdir(session_dir):
            os.makedirs(session_dir)
        return safe_join(session_dir, kwargs['filename'])

    @Debugger
    def new_file(self, **kwargs):
        """
        See :meth:`FileStore.new_file`
        """
        return open(self._filename(**kwargs), 'w')

    @Debugger
    def delete_files(self, session, filename):
        """
        See :meth:`FileStore.delete_files`
        """
        os.path.remove(self._filename(session=session, filename=filename))

    @Debugger
    def get_file(self, session, filename):
        """
        See :meth:`FileStore.get_file`
        """
        f=self._filename(session=session, filename=filename)
        if os.path.exists(f):
            return open(f, 'r')
        else:
            return None

    @Debugger
    def create_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.create_file`
        """
        with self.new_file(**kwargs) as f:
            f.write(file_handle.read())

    @Debugger
    def copy_file(self, file_handle, **kwargs):
        """
        See :meth:`FileStore.copy_file`
        """
        file_handle.write(self.get_file(**kwargs).read())

    @Debugger
    def new_context(self):
        """
        Empty function
        """
        pass

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
    new_file=db_method('new_file',['session', 'filename'], True)
    delete_files=db_method('delete_files',['session', 'filename'], True)
    get_file=db_method('get_file',['session', 'filename'], True)
