import uuid
import zmq
import os
import signal
import tempfile
import json
import random
import sys
import interact_sagecell
import interact_compatibility
from IPython.zmq.ipkernel import IPKernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe

class ForkingKernelManager:
    def __init__(self):
        self.kernels = {}

    def fork_kernel(self, sage_dict, config, q):
        ka = IPKernelApp.instance(config=config)
        ka.initialize([])
        ka.kernel.shell.user_ns.update(sage_dict)
        ka.kernel.shell.user_ns.update(interact_sagecell.imports)
        ka.kernel.shell.user_ns.update(interact_compatibility.imports)
        if "sys" in ka.kernel.shell.user_ns:
            ka.kernel.shell.user_ns["sys"]._update_interact = interact_sagecell.update_interact
        else:
            sys._update_interact = interact_sagecell.update_interact
            ka.kernel.shell.user_ns["sys"] = sys
        ka.kernel.shell.user_ns["interact"] = interact_sagecell.interact_func(ka.session, ka.iopub_socket)
        q.send({"ip": ka.ip, "key": ka.session.key, "shell_port": ka.shell_port,
                "stdin_port": ka.stdin_port, "hb_port": ka.hb_port, "iopub_port": ka.iopub_port})
        q.close()
        ka.start()

    def start_kernel(self, sage_dict=None, kernel_id=None, config=None):
        random.seed()
        if sage_dict is None:
            sage_dict = {}
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config()
        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(sage_dict, config, q))
        proc.start()
        connection = p.recv()
        p.close()
        self.kernels[kernel_id] = (proc, connection)
        return {"kernel_id": kernel_id, "connection": connection}

    def send_signal(self, kernel_id, signal):
        """Send a signal to a running kernel."""
        if kernel_id in self.kernels:
            try:
                os.kill(self.kernels[kernel_id][0].pid, signal)
                self.kernels[kernel_id][0].join()
            except OSError, e:
                # On Unix, we may get an ESRCH error if the process has already
                # terminated. Ignore it.
                from errno import ESRCH
                if e.errno != ESRCH:
                    raise

    def kill_kernel(self, kernel_id):
        """Kill a running kernel."""
        try:
            self.send_signal(kernel_id, signal.SIGTERM)
            del self.kernels[kernel_id]
            return True
        except:
            return False

    def interrupt_kernel(self, kernel_id):
        """Interrupt a running kernel."""
        try:
            self.send_signal(kernel_id, signal.SIGINT)
            return True
        except:
            return False

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
