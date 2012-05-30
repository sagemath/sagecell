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
def launcher(fname, **launch_opts):
    
    cfg = Config()
    cfg.IPKernelApp.connection_file = fname
    from multiprocessing import Process
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
    
    
    
def embed_kernel(**kwargs):
    """Embed and start an IPython kernel in a given scope.
    
    Parameters
    ----------
    kwargs : various, optional
        Further keyword args are relayed to the KernelApp constructor,
        allowing configuration of the Kernel.  Will only have an effect
        on the first embed_kernel call for a given process.
    
    """
    from IPython.zmq.ipkernel import IPKernelApp
    # get the app if it exists, or set it up if it doesn't
    if IPKernelApp.initialized():
        app = IPKernelApp.instance()
    else:
        app = IPKernelApp.instance(**kwargs)
        app.initialize([])
        # TODO: is this needed???
        # Undo unnecessary sys module mangling from init_sys_modules.
        # This would not be necessary if we could prevent it
        # in the first place by using a different InteractiveShell
        # subclass, as in the regular embed case.
        main = app.kernel.shell._orig_sys_modules_main_mod
        if main is not None:
            sys.modules[app.kernel.shell._orig_sys_modules_main_name] = main

    app.start()

if __name__ == '__main__':
    # an example
    start_port = randrange(10000,60000)
    a=ForkingKernelManager()
    # set the key *before* launching, so it will be in the file
    from uuid import uuid4
    a.session.key = str(uuid4())
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
