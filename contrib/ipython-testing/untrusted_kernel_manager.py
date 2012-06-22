from forking_kernel_manager import ForkingKernelManager

class UntrustedMultiKernelManager:
    def __init__(self):
        self.fkm = ForkingKernelManager()
        self._kernels = set()
        try:
            import sage.all
            self.sage_dict = dict([(n,getattr(sage.all, n)) for n in dir(sage.all) if not n.startswith("_")])
        except:
            self.sage_dict = {}
    
    def start_kernel(self, resource_limits=None):
        x = self.fkm.start_kernel(sage_dict=self.sage_dict, resource_limits=resource_limits)
        self._kernels.add(x["kernel_id"])
        return x

    def kill_kernel(self, kernel_id):
        success = self.fkm.kill_kernel(kernel_id)
        if success:
            self._kernels.remove(kernel_id)
        return success

    def interrupt_kernel(self, kernel_id):
        return self.fkm.interrupt_kernel(kernel_id)

    def restart_kernel(self, kernel_id, *args, **kwargs):
        return self.fkm.restart_kernel(self.sage_dict, kernel_id)

    def purge_kernels(self):        
        failures = []
        
        for kernel_id in list(self._kernels):
            success = self.kill_kernel(kernel_id)
            if not success:
                failures.append(kernel_id)
        
        return failures

if __name__ == "__main__":
    x = UntrustedMultiKernelManager()
    y = x.start_kernel()
    print y
    from time import sleep 
    sleep(2)
    print x.restart_kernel(y["kernel_id"])
    sleep(2)
    x.kill_kernel(y["kernel_id"])
