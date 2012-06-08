from forking_kernel_manager import ForkingKernelManager

class UntrustedMultiKernelManager:
    def __init__(self):
        self.fkm = ForkingKernelManager()
    
    def start_kernel(self):
        return self.fkm.start_kernel()

    def kill_kernel(self, kernel_id):
        self.fkm.kill_kernel(kernel_id)

    def interrupt_kernel(self, kernel_id):
        self.fkm.interrupt_kernel(kernel_id)

    def restart_kernel(self, kernel_id, *args, **kwargs):
        self.fkm.restart_kernel(kernel_id)

if __name__ == "__main__":
    x = UntrustedMultiKernelManager()
    y = x.start_kernel()
    print y
    from time import sleep 
    sleep(2)
    x.restart_kernel(y["kernel_id"])
    sleep(2)
    x.kill_kernel(y["kernel_id"])
