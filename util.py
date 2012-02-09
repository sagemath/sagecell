import sys

try:
    from sagecell_config import LOGGING
except ImportError:
    # the untrusted user will probably not have access to the sagecell_config
    # file
    LOGGING=True

def log(message, key=' '):
    if LOGGING:
        sys.__stderr__.write("%s\t: %s\n"%(key, message))

import os
DEFAULT_DIR=''

def write_process_id(prefix=None):
    with open(DEFAULT_DIR+prefix+'sage-cell-pid.%d'%os.getpid(),'w') as f:
        f.write('%d %d %d\n'%(os.getpid(), os.getpgid(0), os.getppid()))

