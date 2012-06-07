import uuid
import zmq
from IPython.zmq.kernelmanager import KernelManager
from multiprocessing import Process, Pipe

class ForkingKernelManager:
    def __init__(self):
        self.kernel_pipes = {}

    def start_kernel(self):
        p, q = Pipe()
        kernel_id = str(uuid.uuid4())
        Process(target=self.fork_kernel, args=(q,)).start()
        self.kernel_pipes[kernel_id] = p
        shell, iopub, stdin, hb = p.recv()
        return {"kernel_id": kernel_id,
                 "ports": {"shell_port": shell, "iopub_port": iopub,
                           "stdin_port": stdin, "hb_port": hb}}

    def kill_kernel(self, kernel_id):
        self.kernel_pipes[kernel_id].send("")
        del self.kernel_pipes[kernel_id]

    def fork_kernel(self, c):
        km = KernelManager()
        km.start_kernel()
        c.send((km.shell_port, km.iopub_port, km.stdin_port, km.hb_port))
        c.recv()
        km.shutdown_kernel()
