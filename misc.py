import sys

def select_db(argv):
    # TODO -- use opt parse
    if len(argv) == 1 or argv[1] == 'mongo':
        import pymongo, db_mongo
        return db_mongo.DB(pymongo.Connection().demo)
    elif argv[1] == 'sqlite':
        import db_sqlite
        return db_sqlite.DB('TODO')
    else:
        sys.exit(1)
