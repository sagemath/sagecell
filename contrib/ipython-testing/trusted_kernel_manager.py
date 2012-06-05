import uuid, random

class TrustedMultiKernelManager:
    """A class for managing multiple kernels on the trusted side."""

    def __init__(self):

        self._kernels = {} #kernel_id: {"comp_id": comp_id, "ports": [hb, iopub, shell, stdin]}
        self._comps = {} #comp_id: {"port": ssh_port, "kernels": {}, "max", #}

    def setup_initial_comps(self):
        """ Tries to read a config file containing initial computer information """
        tmp_comps = {}

        try:
            import config
        except:
            config = object()

        if hasattr(config, "computers"):
            for i in config.computers:
                i["kernels"] = {}
                # this is a hack
                i["port"] = UntrustedMultiKernelManager()
                comp_id = uuid.uuid4()
                tmp_comps[comp_id] = i

        self._comps = tmp_comps

    def purge_kernels(self, c_id):
        """ Kills all kernels on a given computer. """
        comp = self._comps[c_id]["port"]
        for i in self._comps[c_id]["kernels"].keys():
            comp.kill_kernel(i)

    def add_computer(self, config):
        """ Adds a tracked computer. """
        c_id = uuid.uuid4()
        self._comps[c_id] = config

    def remove_computer(self, c_id):
        """ Removes a tracked computer. """
        self.purge_kernels(c_id)
        del self._comps[c_id]

    def new_session(self):
        """Starts a new kernel on an open computer."""
        comp_id = self.find_open_computer()
        comp =  self._comps[comp_id]["port"] #once ssh is implemented this must be changed
        (k_id, k_ports) = comp.start_kernel()
        self._kernels[k_id] = {"comp_id": comp_id, "ports": k_ports}
        self._comps[comp_id]["kernels"][k_id] = None
        print "Kernels ::: ", self._kernels
        return k_id

    def end_session(self, kernel_id):
        """Kills an existing kernel on a given computer."""
        comp_id = self._kernels[kernel_id]["comp_id"]
        comp = self._comps[comp_id]["port"]
        print "Killing Kernel ::: %s at %s"%(kernel_id, str(comp))
        if (comp.kill_kernel(kernel_id)):
            del self._kernels[kernel_id]
            del self._comps[comp_id]["kernels"][kernel_id]
        else:
            print "error ending kernel"
        
    def find_open_computer(self):
        """Returns the comp_id of a computer able to start a new kernel."""
        
        ids = self._comps.keys()
        random.shuffle(ids)
        found_id = None
        done = False
        index = 0        

        while (index < len(ids) - 1 and not done):
            found_id = ids[index]
            if len(self._comps[found_id]["kernels"].keys()) < self._comps[found_id]["max"]:
                done = True
            else:
                index += 1
        if done:
            return found_id
        else:
            raise IOError("Could not find open computer. There are %d computers available."%len(ids))
    
        

""" TO DO:

* SSH connecting to the UMKM
* Have the TMKM manage / start / stop connections from the kernel < -- > server

"""



class UntrustedMultiKernelManager:
    """ This just emulates how a UMKM should work """
    def __init__(self):
        self._kernels = {}

    def start_kernel(self):
        info = (str(uuid.uuid4()), [random.randrange(50000,60000) for i in xrange(4)])
        self._kernels[info[0]] = info[1]
        return info
    def kill_kernel(self, k_id):
        retval = False
        try:
            del self._kernels[k_id]
            retval = True
        except:
            pass

        return retval



if __name__ == "__main__":
    trutest = TrustedMultiKernelManager()

    trutest.setup_initial_comps()

    for i in xrange(60):
        test_id = trutest.new_session()
        trutest.end_session(test_id)

    trutest.new_session()

    for i in trutest._comps.values():
        print i["kernels"]

