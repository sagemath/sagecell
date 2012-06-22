import uuid
import zmq
import os
import signal
import tempfile
import json
import random
import sys
import interact
import resource
from IPython.zmq.ipkernel import IPKernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe

class ForkingKernelManager:
    def __init__(self):
        self.kernels = {}

    def fork_kernel(self, sage_dict, config, q, resource_limits):
        os.setpgrp()
        from resource import setrlimit
        for r, limit in resource_limits.iteritems():
            setrlimit(r, (limit, limit))
        ka = IPKernelApp.instance(config=config)
        ka.initialize([])
        ka.kernel.shell.user_ns.update(sage_dict)
        ka.kernel.shell.user_ns.update(interact.classes)
        if "sys" in ka.kernel.shell.user_ns:
            ka.kernel.shell.user_ns["sys"]._interacts = interact.interacts
        else:
            sys._interacts = interact.interacts
            ka.kernel.shell.user_ns["sys"] = sys
        ka.kernel.shell.user_ns["interact"] = interact.interact_func(ka.session, ka.iopub_socket)
        q.send({"ip": ka.ip, "key": ka.session.key, "shell_port": ka.shell_port,
                "stdin_port": ka.stdin_port, "hb_port": ka.hb_port, "iopub_port": ka.iopub_port})
        q.close()
        ka.start()

    def start_kernel(self, sage_dict=None, kernel_id=None, config=None, resource_limits=None):
        random.seed()
        if sage_dict is None:
            sage_dict = {}
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config()
        if resource_limits is None:
            resource_limits = {}
        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(sage_dict, config, q, resource_limits))
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
