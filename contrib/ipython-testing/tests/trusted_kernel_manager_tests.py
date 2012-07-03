import trusted_kernel_manager
from nose.tools import assert_equal, assert_raises
import random
import os
import sys
import ast
import zmq
from IPython.zmq.session import Session
from contextlib import contextmanager
import time
import misc
configg = misc.Config()
d = configg.get_default_config("_default_config")

testlog = "sagecelltests.log"

@contextmanager
def stdout_redirected(new_stdout):
    save_stdout = sys.stdout
    sys.stdout = new_stdout
    try:
        yield None
    finally:
        sys.stdout = save_stdout

@contextmanager
def opened(filename, mode="r"):
    f = open(filename, mode)
    try:
        yield f
    finally:
        f.close()

class TestTrustedMultiKernelManager:
    def setUp(self): #called automatically before each test is run
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)
        self.a._comps["testcomp1"] = {"host": "localhost",
                                 "port": random.randrange(50000,60000),
                                 "kernels": {"kone": None, "ktwo": None},
                                 "max_kernels": 10,
                                 "beat_interval": 3.0,
                                 "first_beat": 5.0}
        self.a._comps["testcomp2"] = {"host": "localhost",
                                 "port": random.randrange(50000,60000),
                                 "kernels": {"kthree": None},
                                 "max_kernels": 15,
                                 "beat_interval": 2.0,
                                 "first_beat": 4.0}
        self.a._kernels["kone"] = {"comp_id": "testcomp1", "ports": {"hb_port": 50001, "iopub_port": 50002, "shell_port": 50003, "stdin_port": 50004}}
        self.a._kernels["ktwo"] = {"comp_id": "testcomp1", "ports": {"hb_port": 50005, "iopub_port": 50006, "shell_port": 50007, "stdin_port": 50008}}
        self.a._kernels["kthree"] = {"comp_id": "testcomp2", "ports": {"hb_port": 50009, "iopub_port": 50010, "shell_port": 50011, "stdin_port": 50012}}

    def tearDown(self):
        for i in list(self.a._comps):
            if len(i) > 10:
                try:
                    self.a.remove_computer(i)
                except:
                    pass
            

    def test_init(self):
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()
        assert_equal(len(self.a._kernels.keys()), 0)
        assert_equal(len(self.a._comps.keys()), 0)
        assert_equal(len(self.a._clients.keys()),0)
        assert_equal(hasattr(self.a, "context"), True)

    def test_init_parameters(self):
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = {"a": "b"}, kernel_timeout = 3.14)
        assert_equal(self.a.default_computer_config, {"a": "b"})
        assert_equal(self.a.kernel_timeout, 3.14)

    def test_get_kernel_ids_success(self):
        x = self.a.get_kernel_ids("testcomp1")
        y = self.a.get_kernel_ids("testcomp2")
        assert_equal(len(x), 2)
        assert_equal(len(y), 1)
        assert_equal("kone" in x, True)
        assert_equal("ktwo" in x, True)
        assert_equal("kthree" in x, False)
        assert_equal("kthree" in y, True)

    def test_get_kernel_ids_invalid_comp(self):
        x = self.a.get_kernel_ids("testcomp3")
        assert_equal(len(x), 0)
        
    def test_get_kernel_ids_no_args(self):
        self.a._kernels = {"a": None, "b": None, "c": None}
        x = self.a.get_kernel_ids()
        assert_equal(len(x), 3)

    def test_get_hb_info_success(self):
        (b, c) = self.a.get_hb_info("kone")
        assert_equal(b, 3.0)
        assert_equal(c, 5.0)
        (b, c) = self.a.get_hb_info("kthree")
        assert_equal(b, 2.0)
        assert_equal(c, 4.0)
        
    def test_get_hb_info_invalid_kernel_id(self):
        assert_raises(KeyError, self.a.get_hb_info, "blah")

    def test_ssh_untrusted(self):
        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "log_file": None,
                  "max": 15}
        client = self.a._setup_ssh_connection(config["host"], config["username"])
        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                x = self.a._ssh_untrusted(config, client)

        assert_equal(x == None, False)
        assert_equal(len(x), 5)

        f = open(testlog, "r")
        y = f.readline()
        assert_equal("executing " in y, True)
        assert_equal("-python " in y, True)
        assert_equal("receiver.py" in y, True)
        assert_equal("/dev/null" in y, True)
        y = f.readline()
        assert_equal(y, "")

    def test_add_computer_success(self): # depends on _setup_ssh_connection, _ssh_untrusted
        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "log_file": None,
                  "max": 15}
        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                x = self.a.add_computer(config)

        assert_equal(len(str(x)), 36)
        assert_equal(x in self.a._comps, True)
        assert_equal(self.a._comps[x]["host"], "localhost")
        assert_equal(self.a._comps[x]["username"], None)
        assert_equal(self.a._comps[x]["python"], sage + " -python")
        assert_equal(self.a._comps[x]["log_file"], None)
        assert_equal(self.a._comps[x]["max"], 15)
        assert_equal(self.a._comps[x]["beat_interval"], 1)
        assert_equal(self.a._comps[x]["first_beat"], 5)
        assert_equal(self.a._comps[x]["kernels"], {})
        assert_equal("socket" in self.a._clients[x], True)
        assert_equal(self.a._clients[x]["socket"].socket_type, 3)
        assert_equal("ssh" in self.a._clients[x], True)

        f = open(testlog, "r")
        y = f.readline()
        assert_equal("executing " in y, True)
        assert_equal("-python " in y, True)
        assert_equal("receiver.py" in y, True)
        assert_equal("/dev/null" in y, True)
        y = f.readline()
        assert_equal("ZMQ Connection with computer " in y, True)
        assert_equal(" at port " in y, True)
        assert_equal(" established." in y, True)
        y = f.readline()
        assert_equal(y, "")

    def test_setup_ssh_connection_success(self):
        x = self.a._setup_ssh_connection("localhost", username=None)
        assert_equal("AutoAddPolicy" in str(x._policy), True)
        assert_equal(len(x.get_host_keys()), 1)

    def test_purge_kernels_no_kernels(self): # depends on add_computer
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "log_file": None,
                  "max": 15}
        x = self.a.add_computer(config)

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.purge_kernels(x)

        f = open(testlog, "r")
        y = f.readline()
        y = ast.literal_eval(y)
        assert_equal("content" in y, True)
        assert_equal("type" in y, True)
        assert_equal(len(y), 2)
        assert_equal("status" in y["content"], True)
        assert_equal(y["content"]["status"], "All kernels killed!")
        assert_equal(len(y["content"]), 1)
        assert_equal(y["type"], "success")
        y = f.readline()
        assert_equal(y, "")
        assert_equal(self.a._comps[x]["kernels"], {})
        assert_equal(self.a._kernels, {})

    def test_purge_kernels_success(self): # depends on add_computer, new_session
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "log_file": None,
                  "max": 15}
        x = self.a.add_computer(config)
        y = self.a.new_session()
        z = self.a.new_session()

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.purge_kernels(x)

        f = open(testlog, "r")
        y = f.readline()
        y = ast.literal_eval(y)
        assert_equal("content" in y, True)
        assert_equal("type" in y, True)
        assert_equal(len(y), 2)
        assert_equal("status" in y["content"], True)
        assert_equal(y["content"]["status"], "All kernels killed!")
        assert_equal(len(y["content"]), 1)
        assert_equal(y["type"], "success")
        y = f.readline()
        assert_equal(y, "")
        assert_equal(self.a._comps[x]["kernels"], {})
        assert_equal(self.a._kernels, {})

    def test_remove_computer_success(self): # depends on add_computer, new_session
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "log_file": None,
                  "max": 15}
        x = self.a.add_computer(config)
        kern1 = self.a.new_session()
        kern2 = self.a.new_session()
        b = self.a.add_computer(config)
        
        # remove computer with active kernels
        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.remove_computer(x)

        f = open(testlog, "r")
        y = f.readline()
        y = ast.literal_eval(y)
        assert_equal("content" in y, True)
        assert_equal("type" in y, True)
        assert_equal(len(y), 2)
        assert_equal("status" in y["content"], True)
        assert_equal(y["content"]["status"], "All kernels killed!")
        assert_equal(len(y["content"]), 1)
        assert_equal(y["type"], "success")
        y = f.readline()
        assert_equal(y, "")
        assert_equal(kern1 in self.a._kernels, False)
        assert_equal(kern2 in self.a._kernels, False)
        assert_equal(x in self.a._comps, False)

        # remove computer with no kernels
        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.remove_computer(b)

        f = open(testlog, "r")
        y = f.readline()
        y = ast.literal_eval(y)
        assert_equal("content" in y, True)
        assert_equal("type" in y, True)
        assert_equal(len(y), 2)
        assert_equal("status" in y["content"], True)
        assert_equal(y["content"]["status"], "All kernels killed!")
        assert_equal(len(y["content"]), 1)
        assert_equal(y["type"], "success")
        y = f.readline()
        assert_equal(y, "")
        assert_equal(b in self.a._comps, False)

    def test_restart_kernel_success(self): # depends on add_computer, new_session
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "log_file": None,
                  "max": 15}
        x = self.a.add_computer(config)
        kern1 = self.a.new_session()
        kern2 = self.a.new_session()

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.restart_kernel(kern2)

        f = open(testlog, "r")
        y = f.readline()
        y = ast.literal_eval(y)
        assert_equal("content" in y, True)
        assert_equal(len(y["content"]), 2)
        assert_equal("type" in y, True)
        assert_equal(y["type"], "success")
        assert_equal("kernel_id" in y["content"], True)
        assert_equal(len(y["content"]["kernel_id"]), 36)
        assert_equal("connection" in y["content"], True)
        assert_equal(len(y["content"]["connection"]), 6)
        assert_equal("stdin_port" in y["content"]["connection"], True)
        assert_equal(len(str(y["content"]["connection"]["stdin_port"])), 5)
        assert_equal("hb_port" in y["content"]["connection"], True)
        assert_equal(len(str(y["content"]["connection"]["hb_port"])), 5)
        assert_equal("shell_port" in y["content"]["connection"], True)
        assert_equal(len(str(y["content"]["connection"]["shell_port"])), 5)
        assert_equal("iopub_port" in y["content"]["connection"], True)
        assert_equal(len(str(y["content"]["connection"]["iopub_port"])), 5)
        assert_equal("ip" in y["content"]["connection"], True)
        assert_equal(y["content"]["connection"]["ip"], "127.0.0.1")
        assert_equal("key" in y["content"]["connection"], True)
        assert_equal(len(y["content"]["connection"]["key"]), 36)
        y = f.readline()
        assert_equal(y, "")
        
    def test_interrupt_kernel_success(self): # depends on add_computer, new_session
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                          "username": None,
                          "python": sage + " -python",
                          "log_file": None,
                          "max": 15}
        x = self.a.add_computer(config)
        kern1 = self.a.new_session()

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.interrupt_kernel(kern1)

        f = open(testlog, "r")
        y = f.readline()
        assert_equal(" interrupted." in y, True)
        assert_equal("not" in y, False)
        
    def test_new_session_success(self): # depends on add_computer
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                          "username": None,
                          "python": sage + " -python",
                          "log_file": None,
                          "max": 15}
        x = self.a.add_computer(config)

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                kern1 = self.a.new_session()

        assert_equal(kern1 in self.a._kernels, True)
        assert_equal("comp_id" in self.a._kernels[kern1], True)
        assert_equal(len(self.a._kernels[kern1]["comp_id"]), 36)
        assert_equal("connection" in self.a._kernels[kern1], True)
        assert_equal("executing" in self.a._kernels[kern1], True)
        assert_equal(self.a._kernels[kern1]["executing"], False)
        assert_equal("timeout" in self.a._kernels[kern1], True)
        assert_equal(time.time() > self.a._kernels[kern1]["timeout"], True)
        x = self.a._kernels[kern1]["comp_id"]
        assert_equal(kern1 in self.a._comps[x]["kernels"], True)
        assert_equal(type(self.a._sessions[kern1]), type(Session()))

        f = open(testlog, "r")
        y = f.readline()
        assert_equal("CONNECTION FILE ::: " in y, True)
        y = f.readline()
        assert_equal(y, "")

    def test_end_session_success(self): # depends on add_computer, new_session
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

        import config as conf
        sage = conf.sage
        config = {"host": "localhost",
                          "username": None,
                          "python": sage + " -python",
                          "log_file": None,
                          "max": 15}
        x = self.a.add_computer(config)
        kern1 = self.a.new_session()
        kern2 = self.a.new_session()

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.end_session(kern1)

        assert_equal(kern1 not in self.a._kernels.keys(), True)
        for i in self.a._comps.keys():
            assert_equal(kern1 not in self.a._comps[i]["kernels"].keys(), True)

        f = open(testlog, "r")
        y = f.readline()
        assert_equal("Killing Kernel ::: %s at " %kern1 in y, True)
        y = f.readline()
        assert_equal("Kernel %s successfully killed."% kern1 in y, True)
        y = f.readline()
        assert_equal(y, "")

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                self.a.end_session(kern2)

        assert_equal(kern2 not in self.a._kernels.keys(), True)
        for i in self.a._comps.keys():
            assert_equal(kern2 not in self.a._comps[i]["kernels"].keys(), True)

        f = open(testlog, "r")
        y = f.readline()
        assert_equal("Killing Kernel ::: %s at " %kern2 in y, True)
        y = f.readline()
        assert_equal("Kernel %s successfully killed."% kern2 in y, True)
        y = f.readline()
        assert_equal(y, "")

    def test_find_open_computer_success(self):
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)
        self.a._comps["testcomp1"] = {"max_kernels": 3, "kernels": {}}
        self.a._comps["testcomp2"] = {"max_kernels": 5, "kernels": {}}

        for i in xrange(8):
            y = self.a._find_open_computer()
            assert_equal(y == "testcomp1" or y == "testcomp2", True)
            self.a._comps[y]["max_kernels"] -= 1

        try:
            self.a._find_open_computer()
        except IOError as e:
            assert_equal("Could not find open computer. There are 2 computers available.", e.message)

    def test_create_connected_stream(self):
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()
        cfg = {"host": "localhost"}
        port = 51337
        socket_type = zmq.SUB

        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                ret = self.a._create_connected_stream(cfg, port, socket_type)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.SUB)

        f = open(testlog, "r")
        y = f.readline()
        assert_equal(y, "Connecting to: tcp://%s:%i\n" % (cfg["host"], port))
        y = f.readline()
        assert_equal(y, "")

        cfg = {"host": "localhost"}
        port = 51337
        socket_type = zmq.REQ

        ret = self.a._create_connected_stream(cfg, port, socket_type)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.REQ)

        cfg = {"host": "localhost"}
        port = 51337
        socket_type = zmq.DEALER

        ret = self.a._create_connected_stream(cfg, port, socket_type)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.DEALER)

    def test_create_iopub_stream(self): # depends on create_connected_stream
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()
        kernel_id = "kern1"
        comp_id = "testcomp1"
        self.a._kernels[kernel_id] = {"comp_id": comp_id, "connection": {"iopub_port": 50101}}
        self.a._comps[comp_id] = {"host": "localhost"}

        ret = self.a.create_iopub_stream(kernel_id)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.SUB)

    def test_create_shell_stream(self): # depends on create_connected_stream
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()
        kernel_id = "kern1"
        comp_id = "testcomp1"
        self.a._kernels[kernel_id] = {"comp_id": comp_id, "connection": {"shell_port": 50101}}
        self.a._comps[comp_id] = {"host": "localhost"}

        ret = self.a.create_shell_stream(kernel_id)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.DEALER)

    def test_create_hb_stream(self): # depends on create_connected_stream
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()
        kernel_id = "kern1"
        comp_id = "testcomp1"
        self.a._kernels[kernel_id] = {"comp_id": comp_id, "connection": {"hb_port": 50101}}
        self.a._comps[comp_id] = {"host": "localhost"}

        ret = self.a.create_hb_stream(kernel_id)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.REQ)

