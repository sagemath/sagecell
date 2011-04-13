import sys

def select_db(argv):
    # TODO -- use opt parse
    if 'sqlite' in argv:
        import db_sqlite
        import sqlite3
        conn = sqlite3.connect('sqlite.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS cells(device_id BIGINT DEFAULT NULL, input TEXT, output TEXT DEFAULT NULL);")
        conn.close()
        return db_sqlite.DB('sqlite.db'), None # None should be replaced by the sqlite filestore
    elif 'sqlalchemy' in argv:
        import db_sqlalchemy
       
        return db_sqlalchemy.DB('sqlalchemy_sqlite.db'), None # None should be replaced by the sqlite filestore
    else: # choose mongo by default
        import pymongo, db_mongo, filestore
        connection=pymongo.Connection().demo
        return db_mongo.DB(connection), filestore.FileStoreMongo(connection)
    #elif argv[1] == 'dict':
    #    import db_dict
    #    return db_dict.DB({})
