from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
import sys

km = UntrustedMultiKernelManager()
listen = True

context = zmq.Context()
rep = context.socket(zmq.REP)
rep.bind("tcp://127.0.0.1:%s" % (sys.argv[1],))
rep.recv()
rep.send("handshake")
while listen:
    x = rep.recv()
    if x == "start_kernel":
        rep.send_pyobj(km.start_kernel())
    elif x == "kill_kernel":
        rep.send("")
        kernel_id = rep.recv()
        rep.send_pyobj(km.kill_kernel(kernel_id))
    elif x == "purge_kernels":
        for i in km._kernels:
            km.kill_kernel(i)
        rep.send("Kernels purged.")
    elif x == "restart_kernel":
        rep.send("")
        kernel_id = rep.recv()
        km.restart_kernel(kernel_id)
        rep.send("Kernel %s restarted." % (kernel_id))
    elif x == "interrupt_kernel":
        rep.send("")
        kernel_id = rep.recv()
        x = km.interrupt_kernel(kernel_id)
        if x:
            rep.send("Kernel %s was interrupted." % (kernel_id))
        else:
            rep.send("Error interrupting kernel.")
    elif x == "remove_computer":
        listen = False
        for i in km._kernels:
            km.kill_kernel(i)
        rep.send("Ended kernel manager.")
        
"""
from time import sleep
for i in km._kernels:
    km.kill_kernel(i)
    sleep(1)
"""
