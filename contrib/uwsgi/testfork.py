"""
A test forking server

To start a single kernel by forking, do::

    python -i testfork.py
    
The kernel object will be in the ``a`` variable.  When you close the 
python session, the forked kernel will be killed.
"""

from IPython.utils.traitlets import Any
from IPython.zmq.kernelmanager import KernelManager

class ForkingKernelManager(KernelManager):
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
    import json
    from IPython.utils.py3compat import str_to_bytes
    with open(fname) as f:
        cfg = json.loads(f.read())
    kw=dict(ip=cfg['ip'], 
            shell_port = cfg['shell_port'],
            stdin_port = cfg['stdin_port'],
            iopub_port = cfg['iopub_port'],
            hb_port = cfg['hb_port'],
            key = str_to_bytes(key),
            )
    print "Attempting to set key: %r"%key
    
    kw.update(launch_opts)
    from multiprocessing import Process
    import IPython.zmq.ipkernel
    from IPython.zmq.ipkernel import embed_kernel
    print "Starting process with kwargs", kw
    p=Process(target=embed_kernel, kwargs=kw)
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
a.shell_port,a.iopub_port,a.stdin_port,a.hb_port=range(start_port,start_port+4)
a.start_kernel(launcher=launcher)
a.session.key=key
a.start_channels()
s=a.shell_channel
s.execute('1+2')
