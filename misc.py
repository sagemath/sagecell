import sys

sagecell_config_defaults = dict(
    db='sqlalchemy',
    sqlalchemy_config={'uri': 'sqlite:///sqlite.db'},
    )

def get_config(value):
    try:
        import sagecell_config
        return getattr(sagecell_config, value)
    except ImportError:
        return sagecell_config_defaults[value]
    except AttributeError:
        raise KeyError(value)

def mongo_connection():
    """
    Set up a MongoDB connection.
    """
    import pymongo
    mongo_config = get_config('mongo_config')

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
        fs=db #todo: support passing the fs in the command line
    else:
        db=get_config('db')
        try:
            fs=get_config('fs')
        except KeyError:
            fs=db

    if db=="sqlalchemy":
        import db_sqlalchemy
        return_db = db_sqlalchemy.DB(get_config('sqlalchemy_config')['uri'])
    elif db=="mongo":
        import db_mongo
        conn = mongo_connection()
        return_db = db_mongo.DB(conn)
    elif db=="zmq":
        import db_zmq
        return_db = db_zmq.DB(address=sysargs.dbaddress)

    import filestore
    if fs=="sqlalchemy":
        return_fs = filestore.FileStoreSQLAlchemy(get_config('sqlalchemy_config')['uri'])
    elif fs=="mongo":
        mongo_config = get_config('mongo_config')
        if db!="mongo":
            # conn has not been set up yet
            conn = mongo_connection()
        return_fs = filestore.FileStoreMongo(conn)
    elif fs=="zmq":
        return_fs = filestore.FileStoreZMQ(address=sysargs.fsaddress)

    return return_db, return_fs
