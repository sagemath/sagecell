"""
A test forking server

To start a single kernel by forking, do::

    python -i testfork.py
    
The kernel object will be in the ``a`` variable.  When you close the 
python session, the forked kernel will be killed.
"""

from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from IPython.utils.traitlets import Any

from IPython.zmq.kernelmanager import KernelManager
class ForkingKernelManager(KernelManager):
    # the KernelManager insists that `kernel` is a Popen instance
    # but we want to *only* fork and embed, not exec a new process
    kernel = Any()
    def __init__(self, *args, **kwargs):
        super(ForkingKernelManager, self    ).__init__(*args, **kwargs)

a=ForkingKernelManager()
def launcher(**kw):
    from multiprocessing import Process
    from IPython.zmq.ipkernel import embed_kernel
    # get right arguments for embed_kernel to hook up channels
    # for step 1, let's do tcp channels
    # later on, we can override the _bind_socket function in kernelapp
    # to support UDS sockets
    kwargs = dict(shell_port=5000,
                  iopub_port=5001,
                  stdin_port=5002,
                  hb_port=5003)
    
    p=Process(target=embed_kernel, kwargs=kwargs)
    p.start()
    return p

print launcher
a.start_kernel(launcher=launcher)

def killkernel(p):
    """p is the Process object"""
    import os
    os.kill(p.pid,15)
    p.join()

import atexit
from functools import partial
atexit.register(partial(killkernel,a.kernel))

# now print out the iopub_port
import zmq
context = zmq.Context.instance()

