import sys

def mongo_connection():
    """
    Set up a MongoDB connection.
    """
    import pymongo
    mongo_config = sagecell_config.mongo_config

    if '@' in mongo_config['mongo_uri']:
        # password specified, so we need to include the database in the URI
        URI=mongo_config['mongo_uri']+'/'+mongo_config['mongo_db']
    else:
        URI = mongo_config['mongo_uri']
    return pymongo.Connection(URI)

def select_db(sysargs=None, context=None):
    u"""
    Create connections to the database and filestore given in sysargs.

    :arg sysargs: system arguments, created by OptionParser
    :arg context: the context for a \xd8MQ connection, if one is needed
    :type context: zmq.Context
    :returns: a tuple of the form ``(db, fs)``
    """

    if hasattr(sysargs, "db") and sysargs.db is not None:
        db=sysargs.db
    else:
        try:
            import sagecell_config
            db=sagecell_config.db
            fs=sagecell_config.fs if hasattr(sagecell_config, "fs") else db
        except ImportError:
            db = fs = 'sqlalchemy'

    if db=="sqlalchemy":
        import db_sqlalchemy
        return_db = db_sqlalchemy.DB(sagecell_config.sqlalchemy_uri)
    elif db=="mongo":
        import db_mongo
        conn = mongo_connection()
        return_db = db_mongo.DB(conn)
    elif db=="zmq":
        import db_zmq
        return_db = db_zmq.DB(address=sysargs.dbaddress)

    import filestore
    if fs=="sqlalchemy":
        return_fs = filestore.FileStoreSQLAlchemy(sagecell_config.sqlalchemy_uri))
    elif fs=="mongo":
        mongo_config = sagecell_config.mongo_config
        if db!="mongo":
            # conn has not been set up yet
            conn = mongo_connection()
        return_fs = filestore.FileStoreMongo(conn)
    elif fs=="zmq":
        return_fs = filestore.FileStoreZMQ(address=sysargs.fsaddress)

    return return_db, return_fs
