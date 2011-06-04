import sys
LOGGING=True
def log(message, key=' '):
    if LOGGING:
        sys.__stdout__.write("%s\t: %s\n"%(key, message))

import os
DEFAULT_DIR=''

def write_process_id(prefix=None):
    with open(DEFAULT_DIR+prefix+'single-cell-pid.%d'%os.getpid(),'w') as f:
        f.write('%d %d %d\n'%(os.getpid(), os.getpgid(0), os.getppid()))

