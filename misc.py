import sys

def select_db(sysargs, context=None):
    u"""
    Create connections to the database and filestore given in sysargs.

    :arg sysargs: system arguments, created by OptionParser
    :arg context: the context for a \xd8MQ connection, if one is needed
    :type context: zmq.Context
    :returns: a tuple of the form ``(db, fs)``
    """
    try:
        db=sysargs.db
    except:
        try:
            import sagecell_config
            db=sagecell_config.db
        except:
            db='mongo'
    try:
        fs=sysargs.fs
    except:
        try:
            import sagecell_config
            fs=sagecell_config.fs
        except:
            fs=db

    if db=="sqlite":
        import db_sqlite
        import sqlite3
        conn = sqlite3.connect('sqlite.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS cells(device_id BIGINT DEFAULT NULL, input TEXT, output TEXT DEFAULT NULL);")
        conn.close()
        return db_sqlite.DB('sqlite.db'), None # None should be replaced by the sqlite filestore
    elif db=="sqlalchemy":
        import db_sqlalchemy
        return db_sqlalchemy.DB('sqlalchemy_sqlite.db'), None # None should be replaced by the sqlite filestore
    elif db=="mongo":
        import pymongo, db_mongo, filestore
        mongo_config = sagecell_config.mongo_config

        if '@' in mongo_config['mongo_uri']:
            # password specified, so we need to include the database in the URI
            URI=mongo_config['mongo_uri']+'/'+mongo_config['mongo_db']
        else:
            URI = mongo_config['mongo_uri']
        conn=pymongo.Connection(URI)
        return db_mongo.DB(conn), filestore.FileStoreMongo(conn)
    elif db=="zmq":
        import db_zmq, filestore
        return db_zmq.DB(address=sysargs.dbaddress), filestore.FileStoreZMQ(address=sysargs.fsaddress)
