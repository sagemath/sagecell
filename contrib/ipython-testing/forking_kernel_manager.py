import uuid
import zmq
import os
import signal
import tempfile
import json
import random
import sys
import resource
import interact_sagecell
import interact_compatibility
import misc
from IPython.zmq.ipkernel import IPKernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe
import logging
import sage
import sage.all
from sage.misc.interpreter import SageInputSplitter
from IPython.core.inputsplitter import IPythonInputSplitter

sage.misc.misc.EMBEDDED_MODE = {'frontend': 'sagecell'}

class SageIPythonInputSplitter(SageInputSplitter, IPythonInputSplitter):
    """
    This class merely exists so that the IPKernelApp.kernel.shell class does not complain.  It requires
    a subclass of IPythonInputSplitter, but SageInputSplitter is a subclass of InputSplitter instead.
    """
    pass

class ForkingKernelManager(object):
    def __init__(self, filename):
        self.kernels = {}
        self.filename = filename

    def fork_kernel(self, sage_dict, config, pipe, resource_limits, logfile):
        os.setpgrp()
        logging.basicConfig(filename=self.filename,format=str(uuid.uuid4()).split('-')[0]+': %(asctime)s %(message)s',level=logging.DEBUG)
        ka = IPKernelApp.instance(config=config)
        ka.initialize([])
        # this should really be handled in the config, not set separately.
        ka.kernel.shell.input_splitter = SageIPythonInputSplitter()
        user_ns = ka.kernel.shell.user_ns
        user_ns.update(sage_dict)
        user_ns.update(interact_sagecell.imports)
        user_ns.update(interact_compatibility.imports)
        sage_code = """
sage.misc.session.init()

# Ensure unique random state after forking
set_random_seed()
"""
        exec sage_code in user_ns

        class TempClass(object):
            pass
        _sage_ = TempClass()
        _sage_.display_message = misc.display_message
        _sage_.update_interact = interact_sagecell.update_interact
        sys._sage_ = _sage_

        # overwrite Sage's interact command with our own
        user_ns["interact"] = interact_sagecell.interact_func(ka.session, ka.iopub_socket)
        
        for r, limit in resource_limits.iteritems():
            resource.setrlimit(getattr(resource, r), (limit, limit))
        pipe.send({"ip": ka.ip, "key": ka.session.key, "shell_port": ka.shell_port,
                "stdin_port": ka.stdin_port, "hb_port": ka.hb_port, "iopub_port": ka.iopub_port})
        pipe.close()
        ka.start()

    def start_kernel(self, sage_dict=None, kernel_id=None, config=None, resource_limits=None, logfile = None):
        if sage_dict is None:
            sage_dict = {}
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config()
        if resource_limits is None:
            resource_limits = {}
        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(sage_dict, config, q, resource_limits, logfile))
        proc.start()
        connection = p.recv()
        p.close()
        self.kernels[kernel_id] = (proc, connection)
        return {"kernel_id": kernel_id, "connection": connection}

    def kill_kernel(self, kernel_id):
        """Kill a running kernel."""
        success = False

        if kernel_id in self.kernels:
            proc = self.kernels[kernel_id][0]
            try:
                success = True
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.join()
            except Exception as e:
                # On Unix, we may get an ESRCH error if the process has already
                # terminated. Ignore it.
                from errno import ESRCH
                if e.errno !=  ESRCH:
                    success = False
        if success:
            del self.kernels[kernel_id]
        return success

    def interrupt_kernel(self, kernel_id):
        """Interrupt a running kernel."""
        success = False

        if kernel_id in self.kernels:
            try:
                os.kill(self.kernels[kernel_id][0].pid, signal.SIGINT)
                success = True
            except:
                pass

        return success

    def restart_kernel(self, sage_dict, kernel_id):
        ports = self.kernels[kernel_id][1]
        self.kill_kernel(kernel_id)
        return self.start_kernel(sage_dict, kernel_id, Config({"IPKernelApp": ports}))

if __name__ == "__main__":
    a = ForkingKernelManager()
    x=a.start_kernel()
    y=a.start_kernel()
    import time
    time.sleep(5)
    a.kill_kernel(x["kernel_id"])
    a.kill_kernel(y["kernel_id"])
