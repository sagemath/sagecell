"""
A test forking server

To start a single kernel by forking, do::

    python -i testfork.py
    
The kernel object will be in the ``a`` variable.  When you close the 
python session, the forked kernel will be killed.
"""

import sys
from IPython.config.loader import Config
from IPython.utils.traitlets import Any
from IPython.zmq.kernelmanager import KernelManager
from IPython.zmq.blockingkernelmanager import BlockingKernelManager

# only using BlockingKernelManager in this case so that it's usable at the bottom.
# The KernelManager is an incomplete base class, but appropriate for building
# various subclasses.

class ForkingKernelManager(BlockingKernelManager):
    # the KernelManager insists that `kernel` is a Popen instance
    # but we want to *only* fork and embed, not exec a new process
    kernel = Any()
    def __init__(self, *args, **kwargs):
        super(ForkingKernelManager, self    ).__init__(*args, **kwargs)
    # later on, we can override the _bind_socket function
    # to support UDS sockets

    def kill_kernel(self):
        """ Kill the running kernel. """
        if self.has_kernel:
            # Pause the heart beat channel if it exists.
            if self._hb_channel is not None:
                self._hb_channel.pause()

            # Attempt to kill the kernel.
            try:
                import os
                print "Killing kernel process %d . . ."%self.kernel.pid,
                os.kill(self.kernel.pid,15)
                self.kernel.join()
            except OSError, e:
                # In Windows, we will get an Access Denied error if the process
                # has already terminated. Ignore it.
                if sys.platform == 'win32':
                    if e.winerror != 5:
                        raise
                # On Unix, we may get an ESRCH error if the process has already
                # terminated. Ignore it.
                else:
                    from errno import ESRCH
                    if e.errno != ESRCH:
                        raise
            self.kernel = None
        else:
            raise RuntimeError("Cannot kill kernel. No kernel is running!")

# Another thing to try is to modify 
# IPython.zmq.entry_point.base_launch_kernel to launch a kernel using
# fork instead of Popen.
key='45042651-5251-4cc6-af79-0d86c9274060'
def launcher(fname, **launch_opts):
    
    cfg = Config()
    cfg.IPKernelApp.connection_file = fname
    from multiprocessing import Process
    from IPython.zmq.ipkernel import embed_kernel
    print "Starting process with file", fname
    
    p=Process(target=embed_kernel, kwargs={'config' : cfg})
    p.start()

    # make sure p is killed when we leave the program
    def killpid(p):
        """p is the Process object"""
        
        import os
        print "Killing kernel process %d . . ."%p.pid,
        os.kill(p.pid,15)
        p.join()
        print "done"
    import atexit
    from functools import partial
    atexit.register(partial(killpid,p))
    return p
    
start_port = 5021
a=ForkingKernelManager()
# set the key *before* launching, so it will be in the file
a.session.key = key
a.shell_port,a.iopub_port,a.stdin_port,a.hb_port = range(start_port,start_port+4)
a.start_kernel(launcher=launcher)
a.start_channels()

# now try to use it:
s=a.shell_channel


s.execute('print "hello"')
s.execute('print "world"')
# get replies:
s.get_msg()
s.get_msg()

# display output
iopub = a.sub_channel
for msg in iopub.get_msgs():
    if msg['msg_type'] == 'stream':
        content = msg['content']
        print "received %s:" % content['name']
        print content['data']
