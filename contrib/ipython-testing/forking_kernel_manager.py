import uuid
import zmq
import os
import signal
import tempfile
import json
import random
import interact
from IPython.zmq.kernelapp import KernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe

class ForkingKernelManager:
    def __init__(self):
        self.kernels = {}

    def fork_kernel(self, sage_dict, config, connection_file, q):
        ka = KernelApp.instance(config=config, kernel_class="IPython.zmq.ipkernel.Kernel",
                                connection_file=connection_file)
        ka.initialize([])

        """ These are commented out because they're causing the entire thing to hang
        ka.kernel.shell.user_ns.update(sage_dict)
        ka.kernel.shell.user_ns.update(interact.classes)
        ka.kernel.shell.user_ns["sys"]._interacts = interact.interacts
        ka.kernel.shell.user_ns["interact"] = interact.interact_func(ka.session, ka.iopub_socket)
        """
        q.send("")
        q.close()
        ka.start()

    def start_kernel(self, sage_dict={}, kernel_id=None, config=None):
        random.seed()
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config()
        connection_file = "%s/%s.json" % (tempfile.gettempdir(), kernel_id)
        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(sage_dict, config, connection_file, q))
        proc.start()
        p.recv()
        p.close()
        with open(connection_file) as f:
            connection = json.loads(f.read())
        self.kernels[kernel_id] = (proc, connection, connection_file)
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
            try:
                os.remove(self.kernels[kernel_id][2])
            except:
                pass
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
