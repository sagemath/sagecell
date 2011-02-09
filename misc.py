import sys

def select_db(argv):
    # TODO -- use opt parse
    if len(argv) == 1 or argv[1] == 'mongo':
        import pymongo, db_mongo
        return db_mongo.DB(pymongo.Connection().demo)
    elif argv[1] == 'sqlite':
        import db_sqlite
        import sqlite3
        conn = sqlite3.connect('sqlite.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS cells(device_id BIGINT DEFAULT NULL, input TEXT, output TEXT DEFAULT NULL);")
        conn.close()
        return db_sqlite.DB('sqlite.db')
    #elif argv[1] == 'dict':
    #    import db_dict
    #    return db_dict.DB({})
    else:
        sys.exit(1)
