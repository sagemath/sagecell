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
                print "Killing kernel process %d . . ."%p.pid,
                os.kill(p.pid,15)
                p.join()
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



a=ForkingKernelManager()
def launcher(fname, **launch_opts):
    import json
    from IPython.utils.py3compat import str_to_bytes
    with open(fname) as f:
        cfg = json.loads(f.read())
    kw=dict(ip=cfg['ip'], shell_port = cfg['shell_port'],
            stdin_port = cfg['stdin_port'],
            iopub_port = cfg['iopub_port'],
            hb_port = cfg['hb_port'],
            # do we need the key?
            #key = str_to_bytes(cfg['key'])
            )
    print "Key: ",str_to_bytes(cfg['key'])
    
    # for some reason, we get an Unsigned Message error.  Possibly related
    # to not passing some key?
    
    #>>> s=a.shell_channel
    #>>> s.execute('print 1+2')
    #'8ba36d81-50fb-4ba7-bba7-a0d3810cbbf1'
    #>>> [IPKernelApp] Invalid Message
    #Traceback (most recent call last):
    #  File "/Users/grout/projects/ipython-upstream/IPython/zmq/ipkernel.py", line 202, in dispatch_shell
    #    msg = self.session.unserialize(msg, content=True, copy=False)
    #  File "/Users/grout/projects/ipython-upstream/IPython/zmq/session.py", line 719, in unserialize
    #    raise ValueError("Unsigned Message")
    #ValueError: Unsigned Message

    
    kw.update(launch_opts)
    from multiprocessing import Process
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
    
a.shell_port=5021
a.iopub_port=5022
a.stdin_port=5023
a.hb_port=5024
a.start_kernel(launcher=launcher)
a.start_channels()

