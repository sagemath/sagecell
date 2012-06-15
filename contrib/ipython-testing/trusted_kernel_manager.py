import uuid, random
import zmq
from zmq.eventloop.zmqstream import ZMQStream
from IPython.zmq.session import Session
from zmq import ssh
import paramiko
import os

try:
    import config
except:
    import config_default as config

class TrustedMultiKernelManager:
    """A class for managing multiple kernels on the trusted side."""

    def __init__(self):

        self._kernels = {} #kernel_id: {"comp_id": comp_id, "connections": {"key": hmac_key, "hb_port": hb, "iopub_port": iopub, "shell_port": shell, "stdin_port": stdin}}
        self._comps = {} #comp_id: {"host", "", "port": ssh_port, "kernels": {}, "max": #, "beat_interval": Float, "first_beat": Float}
        self._clients = {} #comp_id: zmq req socket object
        self._sessions = {} # kernel_id: Session
        self.context = zmq.Context()

    def get_kernel_ids(self, comp = None):
        ids = []
        if comp is not None and comp in self._comps:
            ids = self._comps[comp]["kernels"].keys()
        elif comp is not None and comp not in self._comps:
            pass
        else:
            ids = self._kernels.keys()
        return ids

    def get_hb_info(self, kernel_id):
        comp_id = self._kernels[kernel_id]["comp_id"]
        comp = self._comps[comp_id]
        return (comp["beat_interval"], comp["first_beat"])

    def setup_initial_comps(self):
        """ Tries to read a config file containing initial computer information """

        if hasattr(config, "computers"):
            for comp in config.computers:
                print comp
                self.add_computer(comp)

    def add_computer(self, config):

        defaults = {"max": 10, "beat_interval": 3.0, "first_beat": 5.0, "kernels": {}}
        comp_id = str(uuid.uuid4())
        cfg = dict(defaults.items() + config.items())

        req = self.context.socket(zmq.REQ)

        port = ssh.tunnel.select_random_ports(1)[0]

        client = self.setup_ssh_connection(cfg["host"], cfg["username"])
        
        code = "python '%s/receiver.py' %d > /tmp/err"%(os.getcwd(), port)
        client.exec_command(code)

        ssh.tunnel_connection(req, "tcp://%s:%s"%(cfg["host"], port), "%s@%s" %(cfg["username"], cfg["host"]), paramiko = True)

        req.send("")
        response = req.recv()
        
        if(response == "handshake"):
            self._clients[comp_id] = req
            self._comps[comp_id] = cfg
            print "ZMQ Connection with computer %s at port %d established." %(comp_id, port)
        else:
            print "ZMQ Connection with computer %s at port %d failed!" %(comp_id, port)

        return comp_id

    def setup_ssh_connection(self, host, username):
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(host, username=username)
        return ssh_client

    def purge_kernels(self, comp_id): #need to update data structures
        """ Kills all kernels on a given computer. """
        req = self._clients[comp_id]
        req.send("purge_kernels")
        print req.recv()
        for i in self._comps[comp_id]["kernels"]:
            #del self._kernels[i]
            pass
        del self._comps[comp_id]["kernels"]

    def shutdown(self):
        """Ends all kernel processes on all computers"""
        for i in self._comps.keys():
            req = self._clients[i]
            req.send("remove_computer")
            req.recv()

    def remove_computer(self, comp_id):
        """ Removes a tracked computer. """
        req = self._clients[comp_id]
        req.send("remove_computer")
        print req.recv()
        for i in self._comps[comp_id]["kernels"]:
            del self._kernels[i]
        del self._comps[comp_id]

    def restart_kernel(self, kernel_id):
        comp_id = self._kernels[kernel_id]["comp_id"]
        req = self._clients[comp_id]
        req.send("restart_kernel")
        req.recv()
        req.send(kernel_id)
        print req.recv()

    def interrupt_kernel(self, kernel_id):
        comp_id = self._kernels[kernel_id]["comp_id"]
        req = self._clients[comp_id]
        req.send("interrupt_kernel")
        req.recv()
        req.send(kernel_id)
        print req.recv()

    def new_session(self):
        """Starts a new kernel on an open computer."""
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
        """Kills an existing kernel on a given computer."""
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
        """Returns the comp_id of a computer able to start a new kernel."""
        
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
        comp_id = self._kernels[kernel_id]["comp_id"]
        host = self._comps[comp_id]["host"]
        connection = self._kernels[kernel_id]["connection"]
        iopub_stream = self._create_connected_stream(host, connection["iopub_port"], zmq.SUB)
        iopub_stream.socket.setsockopt(zmq.SUBSCRIBE, b"")
        return iopub_stream

    def create_shell_stream(self, kernel_id):
        comp_id = self._kernels[kernel_id]["comp_id"]
        host = self._comps[comp_id]["host"]
        connection = self._kernels[kernel_id]["connection"]
        shell_stream = self._create_connected_stream(host, connection["shell_port"], zmq.DEALER)
        return shell_stream

    def create_hb_stream(self, kernel_id):
        comp_id = self._kernels[kernel_id]["comp_id"]
        host = self._comps[comp_id]["host"]
        connection = self._kernels[kernel_id]["connection"]
        hb_stream = self._create_connected_stream(host, connection["hb_port"], zmq.REQ)
        return hb_stream

""" TO DO:

* SSH connecting to the UMKM
* Have the TMKM manage / start / stop connections from the kernel < -- > server

"""




if __name__ == "__main__":
    try:
        t = TrustedMultiKernelManager()
        
        print t.context

        t.setup_initial_comps()

        for i in xrange(10):
            t.new_session()

        vals = t._comps.values()
        for i in xrange(len(vals)):
            print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

        print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())
        
        y = t.get_kernel_ids()

        for i in y:
            t.interrupt_kernel(i)
            #t.restart_kernel(i) appears broken...
            import random
            if random.randrange(0,2):
                t.end_session(i)

        vals = t._comps.values()
        for i in xrange(len(vals)):
            print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

        print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())

        x = t._comps.keys()

        t.remove_computer(x[1])

        vals = t._comps.values()
        for i in xrange(len(vals)):
            print "\nComputer #%d has kernels ::: "%i, vals[i]["kernels"].keys()

        print "\nList of all kernel ids ::: " + str(t.get_kernel_ids())
        
    except:
        # print "errorrrr"
        raise
    finally:
        #for the moment to ensure all receivers are killed...
        for i in t._comps.keys():
            t.remove_computer(i)
    
        
