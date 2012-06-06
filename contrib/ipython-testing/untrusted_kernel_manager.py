from IPython.zmq.kernelmanager import KernelManager #used for testing
import uuid

class UntrustedMultiKernelManager:
    """ This just emulates how a UMKM should work """
    def __init__(self):
        self._kernels = {}

    def start_kernel(self):
        self.kernel_id = str(uuid.uuid4())
        km = KernelManager() #used for testing

        km.start_kernel()

        self._kernels[self.kernel_id] = km

        ports = dict(shell_port = km.shell_port, 
                     iopub_port = km.iopub_port,
                     stdin_port = km.stdin_port,
                     hb_port = km.hb_port)
        return {"kernel_id": self.kernel_id, "ports": ports}

    def kill_kernel(self, kernel_id):
        retval = False    
        try:
            import os
            #pid = self._kernels[kernel_id].pid
            #print pid
            self._kernels[kernel_id].shutdown_kernel()
            #os.killpg(os.getpgid(pid))
            del self._kernels[kernel_id]
            retval = True
        except:
            raise

        return retval

if __name__ == "__main__":
    x = UntrustedMultiKernelManager()
    y = x.start_kernel()
    print y
    from time import sleep 
    sleep(2)
    val = x.kill_kernel(y["kernel_id"])
    print val
