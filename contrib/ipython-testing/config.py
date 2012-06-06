import random

computers = []

for i in xrange(2):
    computers.append({"host": "localhost", "port": random.randrange(50000,60000), "username": "testssh", "max": random.randrange(20,50), "beat_interval": 3.0, "first_beat": 5.0})
