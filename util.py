import sys
LOGGING=True
def log(message, key=' '):
    if LOGGING:
        sys.__stdout__.write("%s\t: %s\n"%(key, message))

