from forking_kernel_manager import ForkingKernelManager, KernelError
import logging

class UntrustedMultiKernelManager(object):
    def __init__(self, filename, ip, update_function=None, tmp_dir=None):
        self.filename = filename
        self.fkm = ForkingKernelManager(self.filename, ip, update_function, tmp_dir=tmp_dir)
        self._kernels = set()
    
    def start_kernel(self, resource_limits=None):
        retry=3
        while retry:
            try:
                x = self.fkm.start_kernel(resource_limits=resource_limits)
                break
            except KernelError as e:
                retry -=1
                logging.debug("kernel error--trying again %s"%retry)
                if not retry:
                    logging.debug("kernel error--giving up %s"%retry)
                    logging.exception(e)
                    raise
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
        return self.fkm.restart_kernel(kernel_id)

    def purge_kernels(self):        
        failures = []
        
        for kernel_id in list(self._kernels):
            success = self.kill_kernel(kernel_id)
            if not success:
                failures.append(kernel_id)
        
        return failures

if __name__ == "__main__":
    def f(x):
        return 1
    x = UntrustedMultiKernelManager("/dev/null", f)
    y = x.start_kernel()
    print y
    from time import sleep 
    sleep(2)
    print x.restart_kernel(y["kernel_id"])
    sleep(2)
    x.kill_kernel(y["kernel_id"])
