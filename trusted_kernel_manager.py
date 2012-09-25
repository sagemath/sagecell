import uuid, random
import zmq
import socket
from zmq.eventloop.zmqstream import ZMQStream
from IPython.zmq.session import Session
from zmq import ssh
import paramiko
import os
import time
from Queue import Queue, Empty

import sender

class TrustedMultiKernelManager(object):
    """ A class for managing multiple kernels on the trusted side. """
    def __init__(self, computers = None, default_computer_config = None,
                 kernel_timeout = None):

        self._kernel_queue = Queue()

        self._kernels = {} #kernel_id: {"comp_id": comp_id, "connection": {"key": hmac_key, "hb_port": hb, "iopub_port": iopub, "shell_port": shell, "stdin_port": stdin}}
        self._comps = {} #comp_id: {"host:"", "port": ssh_port, "kernels": {}, "max": #, "beat_interval": Float, "first_beat": Float, "resource_limits": {resource: limit}}
        self._clients = {} #comp_id: {"ssh": paramiko client}
        self._sessions = {} # kernel_id: Session

        self._sender = sender.AsyncSender() # Manages asynchronous communication

        self.context = zmq.Context()
        self.default_computer_config = default_computer_config

        self.kernel_timeout = kernel_timeout
        if kernel_timeout is None:
            self.kernel_timeout = 0.0

        if computers is not None:
            for comp in computers:
                comp_id = self.add_computer(comp)
                preforked = comp.get("preforked_kernels", 0)
                if preforked:
                    for i in range(preforked):
                        def cb(kernel_id, i=i, comp_id=comp_id):
                            self._kernel_queue.put((kernel_id, comp_id))
                            print "Started preforked kernel %d, computer %s"%(i, comp_id)
                        self.new_session_async(callback = cb, comp_id = comp_id)
                    print "Requested %d preforked kernels"%preforked

    def get_kernel_ids(self, comp = None):
        """ A function for obtaining kernel ids of a particular computer.

        :arg str comp: the id of the computer whose kernels you desire
        :returns: kernel ids of a computer if its id is given or all kernel ids if no id is given
        :rtype: list
        """
        ids = []
        if comp is not None and comp in self._comps:
            ids = self._comps[comp]["kernels"].keys()
        elif comp is not None and comp not in self._comps:
            pass
        else:
            ids = self._kernels.keys()
        return ids

    def get_hb_info(self, kernel_id):
        """ Returns basic heartbeat information for a given kernel. 

        :arg str kernel_id: the id of the kernel whose heartbeat information you desire
        :returns: a tuple containing the kernel's beat interval and time until first beat
        :rtype: tuple
        """
        
        comp_id = self._kernels[kernel_id]["comp_id"]
        comp = self._comps[comp_id]
        return (comp["beat_interval"], comp["first_beat"])

    def _setup_ssh_connection(self, host, username):
        """ Returns a paramiko SSH client connected to the given host. 

        :arg str host: host to SSH to
        :arg str username: username to SSH to
        :returns: a paramiko SSH client connected to the host and username given
        """
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(host, username=username)
        return ssh_client

    def _ssh_untrusted(self, cfg, client):
        logfile = cfg.get("log_file", os.devnull)
        ip = socket.gethostbyname(cfg["host"])
        code = "%s '%s/receiver.py' '%s' '%s'"%(cfg["python"], cfg["location"], ip, logfile)
        ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command(code)
        stdout_channel = ssh_stdout.channel

        # Wait for untrusted side to respond with the bound port using paramiko channels
        # Another option would be to have a short-lived ZMQ socket bound on the trusted
        # side and have the untrusted side connect to that and send the port
        output = ""
        stdout_channel.settimeout(2.0)
        polls = 0
        while output.count("\n")!=2:
            try:
                output += stdout_channel.recv(1024)
            except socket.timeout:
                polls+= 1
            if polls>20:
                return None
            if len(output)==0:
                # connection closed earlier than we thought
                return None
        return int(output.split("\n")[0])

    def add_computer(self, config):
        """ Adds a tracked computer.

        :arg dict config: configuration dictionary of the computer to be added
        :returns: computer id assigned to added computer
        :rtype: string
        """
        defaults = self.default_computer_config
        comp_id = str(uuid.uuid4())
        cfg = dict(defaults.items() + config.items())
        cfg["kernels"] = {}
        req = self.context.socket(zmq.REQ)

        client = self._setup_ssh_connection(cfg["host"], cfg["username"])

        port = self._ssh_untrusted(cfg, client)
        retval = None
        if port is None:
            print "Computer %s did not respond, connecting failed!"%comp_id
        else:
            comp_id = self._sender.register_computer(cfg["host"], port)
            self._clients[comp_id] = {"ssh": client}
            self._comps[comp_id] = cfg
            print "ZMQ Connection with computer %s at port %d established." %(comp_id, port)
            retval = comp_id

        return retval


    def purge_kernels(self, comp_id):
        """ Kills all kernels on a given computer. 

            :arg str comp_id: the id of the computer whose kernels you want to purge
        """
        reply = self._sender.send_msg({"type": "purge_kernels"}, comp_id)

        print reply
        for i in self._comps[comp_id]["kernels"].keys():
            del self._kernels[i]
        self._comps[comp_id]["kernels"] = {}

    def shutdown(self):
        """ Ends all kernel processes on all computers. """
        for comp_id in self._comps.keys():
            self.remove_computer(comp_id)

    def remove_computer(self, comp_id):
        """ Removes a tracked computer. 

        :arg str comp_id: the id of the computer that you want to remove
        """
        ssh_client = self._clients[comp_id]["ssh"]
        reply = self._sender.send_msg({"type": "remove_computer"}, comp_id)
        print reply
        for i in self._comps[comp_id]["kernels"].keys():
            del self._kernels[i]
        ssh_client.close()
        del self._comps[comp_id]
        del self._clients[comp_id]

    def restart_kernel(self, kernel_id):
        """ Restarts a given kernel.

        :arg str kernel_id: the id of the kernel you want restarted
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        reply = self._sender.send_msg({"type": "restart_kernel",
                                       "content": {"kernel_id": kernel_id}},
                                      comp_id)
        print reply

    def interrupt_kernel(self, kernel_id):
        """ Interrupts a given kernel. 

        :arg str kernel_id: the id of the kernel you want interrupted
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        reply = self._sender.send_msg({"type": "interrupt_kernel",
                                       "content": {"kernel_id": kernel_id}},
                                      comp_id)

        if reply["type"] == "success":
            print "Kernel %s interrupted."%kernel_id
        else:
            print "Kernel %s not interrupted!"%kernel_id
        return reply

    def new_session(self, comp_id = None):
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

        resource_limits = self._comps[comp_id].get("resource_limits")
        reply = self._sender.send_msg({"type":"start_kernel", "content": {"resource_limits": resource_limits}}, comp_id)
        if reply["type"] == "success":
            reply_content = reply["content"]
            kernel_id = reply_content["kernel_id"]
            kernel_connection = reply_content["connection"]
            self._kernels[kernel_id] = {"comp_id": comp_id,
                                        "connection": kernel_connection,
                                        "executing": False,
                                        "timeout": time.time()+self.kernel_timeout}
            self._comps[comp_id]["kernels"][kernel_id] = None
            self._sessions[kernel_id] = Session(key=kernel_connection["key"])
            return kernel_id
        else:
            return False

    def _setup_kernel(self, reply, comp_id):
        """
        Set up the kernel information contained in the untrusted reply message `reply` from computer `comp_id`.
        """
        reply_content = reply["content"]
        kernel_id = reply_content["kernel_id"]
        kernel_connection = reply_content["connection"]
        self._kernels[kernel_id] = {"comp_id": comp_id,
                                    "connection": kernel_connection,
                                    "executing": False,
                                    "timeout": time.time()+self.kernel_timeout}
        self._comps[comp_id]["kernels"][kernel_id] = None
        self._sessions[kernel_id] = Session(key=kernel_connection["key"])

    def new_session_async(self, callback=None, comp_id=None):
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
            if comp_id is not None:
                # if we're demanding a specific computer, then we don't want a random
                # preforked kernel
                raise Empty
            preforked_kernel_id, comp_id = self._kernel_queue.get_nowait()
            preforked = True
            def cb(reply):
                if reply["type"] == "success":
                    self._setup_kernel(reply, comp_id)
                    self._kernel_queue.put((reply["content"]["kernel_id"], comp_id))
                else:
                    print "Error restarting preforked kernel"
        except Empty:
            if comp_id is None:
                comp_id = self._find_open_computer()
            preforked = False
            def cb(reply):
                if reply["type"] == "success":
                    self._setup_kernel(reply, comp_id)
                    callback(reply["content"]["kernel_id"])
                else:
                    callback(False)

        resource_limits = self._comps[comp_id].get("resource_limits")
        self._sender.send_msg_async({"type":"start_kernel", "content": {"resource_limits": resource_limits}}, comp_id, callback=cb)

        if preforked:
            # return immediately with preforked kernel
            callback(preforked_kernel_id)

    def end_session(self, kernel_id):
        """ Kills an existing kernel on a given computer.

        :arg str kernel_id: the id of the kernel you want to kill
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        reply = self._sender.send_msg({"type":"kill_kernel",
                                       "content": {"kernel_id": kernel_id}},
                                      comp_id)
        if (reply["type"] == "error"):
            print "Error ending kernel %s!" % (kernel_id,)
        else:
            del self._kernels[kernel_id]
            del self._comps[comp_id]["kernels"][kernel_id]
        
    def _find_open_computer(self):
        """ Randomly searches through computers in _comps to find one that can start a new kernel.

        :returns: the comp_id of a computer with room to start a new kernel
        :rtype: string
        """ 
        
        ids = self._comps.keys()
        random.shuffle(ids)
        found_id = None
        done = False
        index = 0        

        while (index < len(ids) and not done):
            found_id = ids[index]
            if len(self._comps[found_id]["kernels"].keys()) < self._comps[found_id]["max_kernels"]:
                done = True
            else:
                index += 1
        if done:
            return found_id
        else:
            raise IOError("Could not find open computer. There are %d computers available."%len(ids))

    def _create_connected_stream(self, host, port, socket_type):
        sock = self.context.socket(socket_type)
        addr = "tcp://%s:%i" % (host, port)
        sock.connect(addr)
        return ZMQStream(sock)
    
    def create_iopub_stream(self, kernel_id):
        """ Create iopub 0MQ stream between given kernel and the server."""
        comp_id = self._kernels[kernel_id]["comp_id"]
        cfg = self._comps[comp_id]
        connection = self._kernels[kernel_id]["connection"]
        iopub_stream = self._create_connected_stream(connection["ip"], connection["iopub_port"], zmq.SUB)
        iopub_stream.socket.setsockopt(zmq.SUBSCRIBE, b"")
        return iopub_stream

    def create_shell_stream(self, kernel_id):
        """ Create shell 0MQ stream between given kernel and the server.gi

        
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        cfg = self._comps[comp_id]
        connection = self._kernels[kernel_id]["connection"]
        shell_stream = self._create_connected_stream(connection["ip"], connection["shell_port"], zmq.DEALER)
        return shell_stream

    def create_hb_stream(self, kernel_id):
        """ Create heartbeat 0MQ stream between given kernel and the server.

        
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        cfg = self._comps[comp_id]
        connection = self._kernels[kernel_id]["connection"]
        hb_stream = self._create_connected_stream(connection["ip"], connection["hb_port"], zmq.REQ)
        return hb_stream



if __name__ == "__main__":
    import misc
    config = misc.Config()

    initial_comps = config.get_config("computers")
    default_config = config.get_default_config("_default_config")

    t = TrustedMultiKernelManager(computers = initial_comps, default_computer_config = default_config)
    for i in xrange(5):
        t.new_session()
        
    vals = t._comps.values()
    for i in xrange(len(vals)):
        print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

    print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())
        
    y = t.get_kernel_ids()
    x = t._comps.keys()

    t.remove_computer(x[0])
            
    vals = t._comps.values()
    print vals
    for i in xrange(len(vals)):
        print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

    print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())

    # Kill all kernels
    for i in t._comps.keys():
        t.remove_computer(i)
