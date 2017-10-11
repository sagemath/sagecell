import math, random, socket, time, uuid
from Queue import Queue, Empty

from log import logger

import paramiko
import sender
import zmq
from zmq.eventloop.zmqstream import ZMQStream

from jupyter_client.session import Session


class TrustedMultiKernelManager(object):
    """ A class for managing multiple kernels on the trusted side. """
    def __init__(self, computers=None, tmp_dir=None):
        self._kernel_queue = Queue()
        self._kernels = {}
        # kernel_id: {"comp_id": comp_id,
        #             "connection": {"key": hmac_key,
        #                            "hb_port": hb,
        #                            "iopub_port": iopub,
        #                            "shell_port": shell,
        #                            "stdin_port": stdin,
        #                            "referer": referer,
        #                            "remote_ip": remote_ip}}
        self._comps = {}
        # comp_id: {"host: "",
        #           "port": ssh_port,
        #           "kernels": {},
        #           "max": #,
        #           "beat_interval": Float,
        #           "first_beat": Float,
        #           "resource_limits": {resource: limit}}
        self._clients = {}
        # comp_id: {"ssh": paramiko client,
        #           "channel": paramico channel}
        self._sessions = {}
        # kernel_id: Session
        self._sender = sender.AsyncSender() # Manages asynchronous communication
        self.context = zmq.Context()
        self.tmp_dir = tmp_dir
        if computers is not None:
            for comp in computers:
                comp_id = self.add_computer(comp)
                preforked = comp.get("preforked_kernels", 0)
                if preforked:
                    for i in range(preforked):
                        self.new_session_prefork(comp_id)
                    logger.debug("Requested %d preforked kernels" % preforked)

    def get_hb_info(self, kernel_id):
        """ Returns basic heartbeat information for a given kernel. 

        :arg str kernel_id: the id of the kernel whose heartbeat information you desire
        :returns: a tuple containing the kernel's beat interval and time until first beat
        :rtype: tuple
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        comp = self._comps[comp_id]
        return (comp["beat_interval"], comp["first_beat"])

    def add_computer(self, config):
        """ Adds a tracked computer.

        :arg dict config: configuration dictionary of the computer to be added
        :returns: computer id assigned to added computer
        :rtype: string
        """
        config = config.copy()
        config["kernels"] = {}
        comp_id = str(uuid.uuid4())
        host = config["host"]
        ip = socket.gethostbyname(host)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=config["username"])
        command = "{} '{}/receiver.py' '{}' '{}' '{}'".format(
            config["python"], config["location"], ip, comp_id, self.tmp_dir)
        logger.debug(command)
        channel = client.exec_command(command)[0].channel
        # Wait for untrusted side to respond with the bound port using paramiko
        # channels.
        # Another option would be to have a short-lived ZMQ socket bound on the
        # trusted side and have the untrusted side connect to that and send the
        # port
        channel.settimeout(2.0)
        output = ""
        for poll in range(20):
            try:
                output += channel.recv(1024)
            except socket.timeout:
                continue
            if output.count("\n") == 2:
                port = int(output.split("\n")[0])
                self._sender.register_computer(host, port, comp_id=comp_id)
                self._comps[comp_id] = config
                self._clients[comp_id] = {"ssh": client, "channel": channel}
                logger.info(
                    "ZMQ connection with computer %s at port %d established",
                    comp_id, port)
                return comp_id
        logger.error("connection to computer %s failed", comp_id)

    def shutdown(self):
        """ Ends all kernel processes on all computers. """
        for comp_id in self._comps.keys():
            self.remove_computer(comp_id)

    def remove_computer(self, comp_id):
        """ Removes a tracked computer. 

        :arg str comp_id: the id of the computer that you want to remove
        """
        ssh_client = self._clients[comp_id]["ssh"]
        self._sender.send_msg({"type": "remove_computer"}, comp_id)
        for i in self._comps[comp_id]["kernels"]:
            del self._kernels[i]
        ssh_client.close()
        del self._comps[comp_id]
        del self._clients[comp_id]

    def _setup_session(self, reply, comp_id):
        """
        Set up the kernel information contained in the untrusted reply message `reply` from computer `comp_id`.
        """
        reply_content = reply["content"]
        kernel_id = reply_content["kernel_id"]
        kernel_connection = reply_content["connection"]
        self._kernels[kernel_id] = {"comp_id": comp_id,
                                    "connection": kernel_connection,
                                    "executing": 0}
        self._comps[comp_id]["kernels"][kernel_id] = None
        self._sessions[kernel_id] = Session(key=kernel_connection["key"])

    def new_session(self, comp_id=None, limited=True):
        """ Starts a new kernel on an open or provided computer.

        Starts up a new kernel non-asynchronously. This should only be used
        when performance is not an issue (e.g. when initially populating
        the preforked kernel queue on server startup, when asynchronous
        operations don't matter).

        :returns: kernel id assigned to the newly created kernel
        :rtype: string
        """
        if comp_id is None:
            comp_id = self._find_open_computer()
        resource_limits = self._comps[comp_id].get("resource_limits") if limited else None
        reply = self._sender.send_msg(
            {"type":"start_kernel",
             "content": {"resource_limits": resource_limits}},
            comp_id)
        if reply["type"] == "success":
            self._setup_session(reply, comp_id)
            return reply["content"]["kernel_id"]
        else:
            return False

    def new_session_prefork(self, comp_id):
        """
        Start up a new kernel asynchronously on a specified computer and put it
        in the prefork queue. Also check if there are any messages in
        stdout/stderr and fetch them - we don't need/expect anything, but if
        there is accumulation of output computer will eventually lock.
        """
        channel = self._clients[comp_id]["channel"]
        if channel.recv_ready():
            logger.debug("computer %s has stdout output: %s",
                         comp_id, channel.recv(2**15))
        if channel.recv_stderr_ready():
            logger.debug("computer %s has stderr output: %s",
                         comp_id, channel.recv_stderr(2**15))
        
        resource_limits = self._comps[comp_id].get("resource_limits")
        def cb(reply):
            if reply["type"] == "success":
                kernel_id = reply["content"]["kernel_id"]
                self._setup_session(reply, comp_id)
                self._kernel_queue.put((kernel_id, comp_id))
                logger.info("Started preforked kernel on %s: %s", comp_id[:4], kernel_id)
            else:
                logger.error("Error starting prefork kernel on computer %s: %s", comp_id, reply)
        logger.info("Trying to start kernel on %s", comp_id[:4])
        self._sender.send_msg_async(
            {"type":"start_kernel",
             "content": {"resource_limits": resource_limits}},
            comp_id,
            callback=cb)

    def new_session_async(self, referer, remote_ip, timeout, callback):
        """ Starts a new kernel on an open computer.

        We try to get a kernel off a queue of preforked kernels to minimize
        startup time. If we can, we return the preforked kernel id via a
        callback and then start up a new kernel on the preforked queue. If
        the prefork queue is empty (e.g. in the case of a large number of
        requests), then we start up a kernel asynchronously and return that
        kernel id via a callback without starting a new kernel on the
        preforked queue. The preforked queue will repopulate when the number
        of requests goes down.

        :returns: kernel id assigned to the newly created kernel
        :rtype: string
        """
        try:
            timeout = float(timeout)
        except ValueError:
            timeout = 0
        if math.isnan(timeout):
            timeout = 0

        def setup_kernel(kernel_id):
            comp = self._comps[comp_id]
            kernel = self._kernels[kernel_id]
            kernel["referer"] = referer
            kernel["remote_ip"] = remote_ip
            kernel["max_timeout"] = comp["max_timeout"]
            kernel["timeout"] = min(timeout, kernel["max_timeout"])
            now = time.time()
            kernel["hard_deadline"] = now + comp["max_lifespan"]
            kernel["deadline"] = min(
                now + kernel["max_timeout"], kernel["hard_deadline"])
            logger.info("Activated kernel %s on computer %s", kernel_id, comp_id)
            callback(kernel_id)

        try:
            kernel_id, comp_id = self._kernel_queue.get_nowait()
            logger.info(
                "Using kernel on %s.  Queue: %s kernels.",
                comp_id,
                self._kernel_queue.qsize())
            self.new_session_prefork(comp_id)
            setup_kernel(kernel_id)
        except Empty:
            comp_id = self._find_open_computer()
            
            def cb(reply):
                if reply["type"] == "success":
                    self._setup_session(reply, comp_id)
                    setup_kernel(reply["content"]["kernel_id"])
                else:
                    callback(False)

            resource_limits = self._comps[comp_id].get("resource_limits")
            self._sender.send_msg_async(
                {"type":"start_kernel",
                 "content": {"resource_limits": resource_limits}},
                comp_id,
                callback=cb)

    def end_session(self, kernel_id):
        """ Kills an existing kernel on a given computer.

        This function is asynchronous

        :arg str kernel_id: the id of the kernel you want to kill
        """
        if kernel_id not in self._kernels:
            return
        comp_id = self._kernels[kernel_id]["comp_id"]
        def cb(reply):
            if (reply["type"] == "error"):
                logger.info(
                    "Error while ending kernel %s Reply %s", kernel_id, reply)
            else:
                logger.info("Ended kernel %s", kernel_id)
                del self._kernels[kernel_id]
                del self._comps[comp_id]["kernels"][kernel_id]

        self._sender.send_msg_async({"type":"kill_kernel",
                                       "content": {"kernel_id": kernel_id}},
                                      comp_id, callback=cb)
        
    def _find_open_computer(self):
        """ Randomly searches through computers in _comps to find one that can start a new kernel.

        :returns: the comp_id of a computer with room to start a new kernel
        :rtype: string
        """ 
        ids = self._comps.keys()
        random.shuffle(ids)
        for id in ids:
            comp = self._comps[id]
            if len(comp["kernels"]) < comp["max_kernels"]:
                return id
        raise IOError("Could not find open computer. There are %d computers available."%len(ids))

    def _create_connected_stream(self, host, port, socket_type):
        sock = self.context.socket(socket_type)
        addr = "tcp://%s:%i" % (host, port)
        sock.connect(addr)
        return ZMQStream(sock)
    
    def create_iopub_stream(self, kernel_id):
        """ Create iopub 0MQ stream between given kernel and the server."""
        connection = self._kernels[kernel_id]["connection"]
        iopub_stream = self._create_connected_stream(connection["ip"], connection["iopub_port"], zmq.SUB)
        iopub_stream.socket.setsockopt(zmq.SUBSCRIBE, b"")
        return iopub_stream

    def create_shell_stream(self, kernel_id):
        """ Create shell 0MQ stream between given kernel and the server.gi
        """
        connection = self._kernels[kernel_id]["connection"]
        shell_stream = self._create_connected_stream(connection["ip"], connection["shell_port"], zmq.DEALER)
        return shell_stream

    def create_hb_stream(self, kernel_id):
        """ Create heartbeat 0MQ stream between given kernel and the server.
        """
        connection = self._kernels[kernel_id]["connection"]
        hb_stream = self._create_connected_stream(connection["ip"], connection["hb_port"], zmq.REQ)
        return hb_stream
        
    def kernel_info(self, kernel_id):
        return self._kernels[kernel_id]
