from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
import sys

km = UntrustedMultiKernelManager()

context = zmq.Context()
rep = context.socket(zmq.REP)
rep.connect("tcp://127.0.0.1:%s" % (sys.argv[1],))
rep.recv()
rep.send("handshake")
while True:
    x = rep.recv()
    if x == "start_kernel":
        rep.send_pyobj(km.start_kernel())
    elif x == "kill_kernel":
        rep.send("")
        kernel_id = rep.recv()
        rep.send_pyobj(km.kill_kernel(kernel_id))
    elif x == "purge_kernels":
        for i in km._kernels.keys():
            km.kill_kernel(i)
        rep.send("got em!")
