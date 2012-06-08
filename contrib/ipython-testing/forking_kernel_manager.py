import uuid
import zmq
import os
import signal
from IPython.zmq.kernelapp import KernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe

class ForkingKernelManager:
    def __init__(self):
        self.kernels = {}

    def start_kernel(self, kernel_id=str(uuid.uuid4()), config=Config()):
        ka = KernelApp.instance(config=config)
        ka.initialize()
        ports = {"shell_port": ka.shell_port, "iopub_port": ka.iopub_port,
                 "stdin_port": ka.stdin_port, "hb_port": ka.hb_port}
        print ports
        proc = Process(target=ka.start)
        proc.start()
        self.kernels[kernel_id] = (ka, proc, ports)
        return {"kernel_id": kernel_id, "ports": ports}

    def send_signal(self, kernel_id, signal):
        """Send a signal to a running kernel."""
        if kernel_id in self.kernels:
            try:
                os.kill(self.kernels[kernel_id][1].pid, signal)
                self.kernels[kernel_id][1].join()
            except OSError, e:
                # On Unix, we may get an ESRCH error if the process has already
                # terminated. Ignore it.
                from errno import ESRCH
                if e.errno != ESRCH:
                    raise

    def kill_kernel(self, kernel_id):
        """Kill a running kernel."""
        self.kernels[kernel_id][0].shell_socket.close()
        self.kernels[kernel_id][0].iopub_socket.close()
        self.kernels[kernel_id][0].stdin_socket.close()
        self.send_signal(kernel_id, signal.SIGTERM)
        self.kernels[kernel_id][1].join()
        del self.kernels[kernel_id]

    def interrupt_kernel(self, kernel_id):
        """Interrupt a running kernel."""
        self.send_signal(kernel_id, signal.SIGINT)

    def restart_kernel(self, kernel_id):
        ports = self.kernels[kernel_id][2]
        self.kill_kernel(kernel_id)
        self.start_kernel(kernel_id, Config({"IPKernelApp": ports}))
