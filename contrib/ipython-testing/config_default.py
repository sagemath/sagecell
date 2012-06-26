import random, os

sage = "sage"

db = "sqlalchemy"
db_config = {}

if db == "sqlalchemy":
    db_config["uri"] = "sqlite:///sqlite.db"


computers = []

for i in xrange(2):
    computers.append({"host": "localhost", "username": "", "python": sage + " -python"})
