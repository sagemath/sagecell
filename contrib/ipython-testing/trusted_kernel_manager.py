import uuid, random
import zmq
from zmq.eventloop.zmqstream import ZMQStream
from IPython.zmq.session import Session
import paramiko
import os

class TrustedMultiKernelManager:
    """ A class for managing multiple kernels on the trusted side. """
    def __init__(self):
        self._kernels = {} #kernel_id: {"comp_id": comp_id, "connection": {"key": hmac_key, "hb_port": hb, "iopub_port": iopub, "shell_port": shell, "stdin_port": stdin}}
        self._comps = {} #comp_id: {"host", "", "port": ssh_port, "kernels": {}, "max": #, "beat_interval": Float, "first_beat": Float}
        self._clients = {} #comp_id: zmq req socket object
        self._sessions = {} # kernel_id: Session
        self.context = zmq.Context()

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

    def setup_initial_comps(self):
        """ Tries to read a config file containing initial computer information. """
        tmp_comps = {}

        try:
            import config
        except:
            config = object()

        defaults = {"max": 10, "beat_interval": 3.0, "first_beat": 5.0}

        context = self.context

        if hasattr(config, "computers"):
            for i in config.computers:
                i["kernels"] = {}
                comp_id = str(uuid.uuid4())
                x = dict(defaults.items() + i.items())
                tmp_comps[comp_id] = x
                req = context.socket(zmq.REQ)
                port = req.bind_to_random_port("tcp://127.0.0.1")
                client = self._setup_ssh_connection(x["host"],x["username"])
                client.exec_command("sage '%s/receiver.py' %d" % (os.getcwd(), port))
                req.send("")
                if(req.recv() == "handshake"):
                    self._clients[comp_id] = req
                    print "ZMQ Connection with computer %s at port %d established." %(comp_id, port)
                
        self._comps = tmp_comps

    def _setup_ssh_connection(self, host, username):
        """ Returns a paramiko SSH client connected to the given host. 

        :arg str host: host to SSH to
        :arg str username: username to SSH to
        :returns: a paramiko SSH client connected to the host and username given
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username)
        return ssh

    def purge_kernels(self, comp_id):
        """ Kills all kernels on a given computer. 

        :arg str comp_id: the id of the computer whose kernels you want to purge
        """
        req = self._clients[comp_id]
        req.send("purge_kernels")
        print req.recv()
        for i in self._comps[comp_id]["kernels"].keys():
            del self._kernels[i]
        self._comps[comp_id]["kernels"] = {}

    def add_computer(self, config):
        """ Adds a tracked computer. 

        :arg dict config: configuration dictionary of the computer to be added
        :returns: computer id assigned to added computer
        :rtype: string
        """
        comp_id = uuid.uuid4()
        self._comps[comp_id] = config
        return comp_id

    def shutdown(self):
        """ Ends all kernel processes on all computers. """
        for i in self._comps.keys():
            req = self._clients[i]
            req.send("remove_computer")
            req.recv()

    def remove_computer(self, comp_id):
        """ Removes a tracked computer. 

        :arg str comp_id: the id of the computer that you want to remove
        """
        req = self._clients[comp_id]
        req.send("remove_computer")
        print req.recv()
        for i in self._comps[comp_id]["kernels"].keys():
            del self._kernels[i]
        del self._comps[comp_id]

    def restart_kernel(self, kernel_id):
        """ Restarts a given kernel.

        :arg str kernel_id: the id of the kernel you want restarted
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        req = self._clients[comp_id]
        req.send("restart_kernel")
        req.recv()
        req.send(kernel_id)
        print req.recv()

    def interrupt_kernel(self, kernel_id):
        """ Interrupts a given kernel. 

        :arg str kernel_id: the id of the kernel you want interrupted
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        req = self._clients[comp_id]
        req.send("interrupt_kernel")
        req.recv()
        req.send(kernel_id)
        print req.recv()

    def new_session(self):
        """ Starts a new kernel on an open computer. 

        :returns: kernel id assigned to the newly created kernel
        :rtype: string
        """
        comp_id = self._find_open_computer()
        
        req = self._clients[comp_id]
        req.send("start_kernel")
        x = req.recv_pyobj()
        kernel_id=x["kernel_id"]
        kernel_connection=x["connection"]

        self._kernels[kernel_id] = {"comp_id": comp_id, "connection": kernel_connection}
        self._comps[comp_id]["kernels"][kernel_id] = None
        self._sessions[kernel_id] = Session(key=kernel_connection["key"])
        return kernel_id

    def end_session(self, kernel_id):
        """ Kills an existing kernel on a given computer.

        :arg str kernel_id: the id of the kernel you want to kill
        """
        comp_id = self._kernels[kernel_id]["comp_id"]

        req = self._clients[comp_id]
        req.send("kill_kernel")
        print "Killing Kernel ::: %s at %s"%(kernel_id, (comp_id))
        req.recv()
        req.send(kernel_id)
        status = req.recv_pyobj()
        
        if (status):
            del self._kernels[kernel_id]
            del self._comps[comp_id]["kernels"][kernel_id]
        else:
            print "error ending kernel"
        
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
            if len(self._comps[found_id]["kernels"].keys()) < self._comps[found_id]["max"]:
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
        print "Connecting to: %s" % addr
        sock.connect(addr)
        return ZMQStream(sock)
    
    def create_iopub_stream(self, kernel_id):
        """ Create iopub 0MQ stream between given kernel and the server.

        
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        host = self._comps[comp_id]["host"]
        connection = self._kernels[kernel_id]["connection"]
        iopub_stream = self._create_connected_stream(host, connection["iopub_port"], zmq.SUB)
        iopub_stream.socket.setsockopt(zmq.SUBSCRIBE, b"")
        return iopub_stream

    def create_shell_stream(self, kernel_id):
        """ Create shell 0MQ stream between given kernel and the server.gi

        
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        host = self._comps[comp_id]["host"]
        connection = self._kernels[kernel_id]["connection"]
        shell_stream = self._create_connected_stream(host, connection["shell_port"], zmq.DEALER)
        return shell_stream

    def create_hb_stream(self, kernel_id):
        """ Create heartbeat 0MQ stream between given kernel and the server.

        
        """
        comp_id = self._kernels[kernel_id]["comp_id"]
        host = self._comps[comp_id]["host"]
        connection = self._kernels[kernel_id]["connection"]
        hb_stream = self._create_connected_stream(host, connection["hb_port"], zmq.REQ)
        return hb_stream



if __name__ == "__main__":
    try:
        t = TrustedMultiKernelManager()

        t.setup_initial_comps()

        for i in xrange(10):
            t.new_session()

        vals = t._comps.values()
        for i in xrange(len(vals)):
            print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

        print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())
        
        y = t.get_kernel_ids()
        x = t._comps.keys()

        t.remove_computer(x[0])

        vals = t._comps.values()
        for i in xrange(len(vals)):
            print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

        print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())

        t.remove_computer(x[1])

        vals = t._comps.values()
        for i in xrange(len(vals)):
            print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

        print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())
        
    except:
        print "errorrrr"
    finally:
        #for the moment to ensure all receivers are killed...
        for i in t._comps.keys():
            t.remove_computer(i)
    
        
