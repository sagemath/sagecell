import trusted_kernel_manager
#from untrusted_kernel_manager import UntrustedMultiKernelManager
from nose.tools import assert_equal, assert_raises
import random
import os
import sys
import ast
from contextlib import contextmanager

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
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()
        self.a._comps["testcomp1"] = {"host": "localhost",
                                 "port": random.randrange(50000,60000),
                                 "kernels": {"kone": None, "ktwo": None},
                                 "max": 10,
                                 "beat_interval": 3.0,
                                 "first_beat": 5.0}
        self.a._comps["testcomp2"] = {"host": "localhost",
                                 "port": random.randrange(50000,60000),
                                 "kernels": {"kthree": None},
                                 "max": 15,
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

    def test_add_computer_success(self):
        with opened(testlog, "w") as f:
            with stdout_redirected(f):
                import config as conf
                sage = conf.sage
                config = {"host": "localhost",
                                  "username": None,
                                  "python": sage + " -python",
                                  "log_file": None,
                                  "max": 15}
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
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()

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
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()

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
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()

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
        client = self.a._clients[x]["ssh"]
        # ensures the client is closed, but perhaps remove_computer should delete it from tmkm._clients instead?
        # we also leave the request socket in _clients... maybe should clean up?
        assert_raises(AttributeError, client.exec_command, "print 'hi'")
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
        client = self.a._clients[b]["ssh"]
        assert_raises(AttributeError, client.exec_command, "print 'hi'")
        assert_equal(b in self.a._comps, False)

    def test_restart_kernel_success(self): # depends on add_computer, new_session
        self.a = trusted_kernel_manager.TrustedMultiKernelManager()

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
        









