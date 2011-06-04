import sys
def log(message, key=' '):
    sys.__stdout__.write("%s\t: %s\n"%(key, message))
    pass

