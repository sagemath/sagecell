import random, os

sage = ""
if sage == "":
    sage = os.environ["SAGE_ROOT"]+"/sage"

db = "sqlalchemy"
db_config = {}

if db == "sqlalchemy":
    db_config["uri"] = "sqlite:///sqlite.db"


computers = []

for i in xrange(2):
    computers.append({"host": "localhost", "username": "", "python": sage + " -python"})
