#! /usr/bin/env python

r"""
Kernel Provider starts compute kernels and sends connection info to Dealer.
"""


import argparse
import errno
from multiprocessing import Process
import os
import resource
import signal
import sys
import time
import uuid

from ipykernel.kernelapp import IPKernelApp
import zmq

import kernel_init
import log
logger = log.provider_logger.getChild(str(os.getpid()))


class KernelProcess(Process):
    """
    Kernel from the provider point of view.
    
    Configures a kernel process and does its best at cleaning up.
    """
    
    def __init__(self, id, rlimits, dir, waiter_port):
        super(KernelProcess, self).__init__()
        self.id = id
        self.rlimits = rlimits
        self.dir = dir
        self.waiter_port = waiter_port

    def run(self):
        global logger
        logger = log.kernel_logger.getChild(str(os.getpid()))
        logger.debug("forked kernel is running")
        log.std_redirect(logger)
        # Close the global Context instance inherited from the parent process.
        zmq.Context.instance().term()
        # Become a group leader for cleaner exit.
        os.setpgrp()
        dir = os.path.join(self.dir, self.id)
        try:
            os.mkdir(dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        os.chdir(dir)
        #config = traitlets.config.loader.Config({"ip": self.ip})
        #config.HistoryManager.enabled = False
        app = IPKernelApp.instance(log=logger)
        from namespace import InstrumentedNamespace
        app.user_ns = InstrumentedNamespace()
        app.initialize([])  # Redirects stdout/stderr
        #log.std_redirect(logger)   # Uncomment for debugging
        # This function should be called via atexit, but it isn't, perhaps due
        # to forking. Stale connection files do cause problems.
        app.cleanup_connection_file()
        kernel_init.initialize(app.kernel)
        for r, limit in self.rlimits.iteritems():
            resource.setrlimit(getattr(resource, r), (limit, limit))
        logger.debug("kernel ready")
        context = zmq.Context.instance()
        socket = context.socket(zmq.PUSH)
        socket.connect("tcp://localhost:{}".format(self.waiter_port))
        socket.send_json({
            "id": self.id,
            "connection": {
                "key": app.session.key,                
                "ip": app.ip,
                "hb": app.hb_port,
                "iopub": app.iopub_port,
                "shell": app.shell_port,
                },
            "rlimits": self.rlimits,
            })
            
        def signal_handler(signum, frame):
            logger.info("received %s, shutting down", signum)
            # TODO: this may not be the best way to do it.
            app.kernel.do_shutdown(False)

        signal.signal(signal.SIGTERM, signal_handler)
        app.start()
        logger.debug("Kernel.run finished")


class KernelProvider(object):
    r"""
    Kernel Provider handles compute kernels on the worker side.
    """
    
    def __init__(self, dealer_address, dir):
        self.is_active = False
        self.dir = dir
        try:
            os.mkdir(dir)
            logger.warning("created parent directory for kernels, "
                "consider doing it yourself with appropriate attributes")
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        context = zmq.Context.instance()
        context.IPV6 = 1
        self.dealer = context.socket(zmq.DEALER)
        logger.debug("connecting to %s", address)
        self.dealer.connect(address)
        self.dealer.send_json("get settings")
        if not self.dealer.poll(5000):
            logger.debug("dealer does not answer, terminating")
            exit(1)
        reply = self.dealer.recv_json()
        logger.debug("received %s", reply)
        assert reply[0] == "settings"
        self.preforked_rlimits = reply[1].pop("preforked_rlimits")
        self.max_kernels = reply[1].pop("max_kernels")
        self.max_preforked = reply[1].pop("max_preforked")
        self.waiter = context.socket(zmq.PULL)
        self.waiter_port = self.waiter.bind_to_random_port("tcp://*")
        self.kernels = dict()   # id: KernelProcess
        self.forking = None
        self.preforking = None
        self.preforked = []
        self.ready_sent = False
        self.to_kill = []
        setup_sage()

    def fork(self, rlimits):
        r"""
        Start a new kernel by forking.
        
        INPUT:
        
        - ``rlimits`` - dictionary with keys ``resource.RLIMIT_*``
        
        OUTPUT:
        
        - ID of the forked kernel
        """
        logger.debug("fork with rlimits %s", rlimits)
        id = str(uuid.uuid4())
        kernel = KernelProcess(id, rlimits, self.dir, self.waiter_port)
        kernel.start()
        self.kernels[id] = kernel
        return id
        
    def kill_check(self):
        """
        Kill old kernels.
        """
        to_kill = []
        for kernel in self.to_kill:
            if kernel.is_alive():
                if time.time() < kernel.deadline:
                    to_kill.append(kernel)
                    continue
                else:
                    logger.warning(
                        "kernel process %d did not stop by deadline",
                        kernel.pid)
            try:
                # Kernel PGID is the same as PID
                os.killpg(kernel.pid, signal.SIGKILL)
            except OSError as e:
                if e.errno !=  errno.ESRCH:
                    raise
            logger.debug("killed kernel process group %d", kernel.pid)
        self.to_kill = to_kill
        
    def send_kernel(self, msg):
        self.dealer.send_json(["kernel", msg])

    def start(self):
        self.is_active = True
        poller = zmq.Poller()
        poller.register(self.dealer, zmq.POLLIN)
        poller.register(self.waiter, zmq.POLLIN)
        while self.is_active:
            # For pretty red lines in the log
            #logger.error("%s %s %s",
            #    self.forking, self.preforking, self.to_kill)
            
            # Tell the dealer if we are ready.
            if (not self.ready_sent
                and self.forking is None
                and (self.preforked or len(self.kernels) < self.max_kernels)):
                self.dealer.send_json("ready")
                self.ready_sent = True
            # Kill old kernel process groups.
            self.kill_check()
            # Process requests from the dealer ...
            events = dict(poller.poll(100))
            if self.dealer in events:
                msg = self.dealer.recv_json()
                logger.debug("received %s", msg)
                if msg == "disconnect":
                    self.stop()
                if msg[0] == "get":
                    # We expect a single "get" for every "ready" sent.
                    self.ready_sent = False
                    if msg[1] == self.preforked_rlimits and self.preforked:
                        self.send_kernel(self.preforked.pop(0))
                        logger.debug("%d preforked kernels left",
                                     len(self.preforked))
                    elif msg[1] == self.preforked_rlimits and self.preforking:
                        self.forking = self.preforking
                        self.preforking = None
                    else:
                        if len(self.kernels) == self.max_kernels:
                            logger.warning("killing a preforked kernel to "
                                "provide a special one")
                            self.stop_kernel(self.preforked.pop(0)["id"])
                        self.forking = self.fork(msg[1])
                if msg[0] == "stop":
                    self.stop_kernel(msg[1])
            # ... and connection info from kernels.
            if self.waiter in events:
                msg = self.waiter.recv_json()
                if self.forking == msg["id"]:
                    self.send_kernel(msg)
                    self.forking = None
                if self.preforking == msg["id"]:
                    self.preforked.append(msg)
                    self.preforking = None
            # Prefork more standard kernels.
            if (not (self.forking or self.preforking)
                and len(self.preforked) < self.max_preforked
                and len(self.kernels) < self.max_kernels):
                self.preforking = self.fork(self.preforked_rlimits)
        for id in self.kernels.keys():
            self.stop_kernel(id)
        while self.to_kill:
            self.kill_check()
            time.sleep(0.1)
            
    def stop(self):
        self.is_active = False
        
    def stop_kernel(self, id):
        kernel = self.kernels.pop(id)
        if kernel.is_alive():
            logger.debug("killing kernel process %d", kernel.pid)
            os.kill(kernel.pid, signal.SIGTERM)
        kernel.deadline = time.time() + 1
        self.to_kill.append(kernel)

            
def setup_sage():
    import sage
    import sage.all
    # override matplotlib and pylab show functions
    # TODO: use something like IPython's inline backend
    
    def mp_show(savefig):
        filename = "%s.png" % uuid.uuid4()
        savefig(filename)
        msg = {"text/image-filename": filename}
        sys._sage_.sent_files[filename] = os.path.getmtime(filename)
        sys._sage_.display_message(msg)
        
    from functools import partial
    import pylab
    pylab.show = partial(mp_show, savefig=pylab.savefig)
    import matplotlib.pyplot
    matplotlib.pyplot.show = partial(mp_show, savefig=matplotlib.pyplot.savefig)

    # The first plot takes about 2 seconds to generate (presumably
    # because lots of things, like matplotlib, are imported).  We plot
    # something here so that worker processes don't have this overhead
    try:
        sage.all.plot(1, (0, 1))
    except Exception:
        logger.exception("plotting exception")


if __name__ == "__main__":        
    parser = argparse.ArgumentParser(
        description="Launch a kernel provider for SageMathCell")
    parser.add_argument("--address",
        help="address of the kernel dealer (defaults to $SSH_CLIENT)")
    parser.add_argument("port", type=int,
        help="port of the kernel dealer")
    parser.add_argument("dir",
        help="directory name for user files saved by kernels")
    args = parser.parse_args()

    log.std_redirect(logger)
    address = args.address or os.environ["SSH_CLIENT"].split()[0]
    if ":" in address:
        address = "[{}]".format(address)
    address = "tcp://{}:{}".format(address, args.port)
    provider = KernelProvider(address, args.dir)

    def signal_handler(signum, frame):
        logger.info("received %s, shutting down", signum)
        provider.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    provider.start()
