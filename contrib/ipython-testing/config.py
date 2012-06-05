import random

computers = []

for i in xrange(5):
    computers.append({"port": random.randrange(50000,60000), "max": random.randrange(20,50)})

