import random, os

sage = ""
if sage == "":
    sage = os.environ["SAGE_ROOT"]+"/sage"

computers = []

for i in xrange(2):
    computers.append({"host": "localhost", "username": "", "python": sage + " -python"})
