import uuid
import zmq
import os
import signal
import tempfile
import json
from IPython.zmq.kernelapp import KernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe

class ForkingKernelManager:
    def __init__(self):
        self.kernels = {}

    def fork_kernel(self, config, connection_file, q):
        ka = KernelApp.instance(config=config)
        ka.connection_file = connection_file
        ka.initialize([])
        q.send("")
        q.close()
        ka.start()

    def start_kernel(self, kernel_id=None, config=None):
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config()
        connection_file = "%s/%s.json" % (tempfile.gettempdir(), kernel_id)
        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(config, connection_file, q))
        proc.start()
        p.recv()
        p.close()
        with open(connection_file) as f:
            ports = json.loads(f.read())
        self.kernels[kernel_id] = (proc, ports)
        return {"kernel_id": kernel_id, "ports": ports}

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

    def restart_kernel(self, kernel_id):
        ports = self.kernels[kernel_id][1]
        self.kill_kernel(kernel_id)
        return self.start_kernel(kernel_id, Config({"IPKernelApp": ports}))

if __name__ == "__main__":
    a = ForkingKernelManager()
    x=a.start_kernel()
    y=a.start_kernel()
    import time
    time.sleep(5)
    a.kill_kernel(x["kernel_id"])
    a.kill_kernel(y["kernel_id"])
