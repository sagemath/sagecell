from trusted_kernel_manager import TrustedMultiKernelManager
from untrusted_kernel_manager import UntrustedMultiKernelManager
from nose.tools import assert_equal, assert_not_equal, assert_raises, raises
import random    

class TestTrustedMultiKernelManager:
    def setUp(self): #called automatically before each test is run
        self.a = TrustedMultiKernelManager()
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
        pass

    def test_init(self):
        self.a = TrustedMultiKernelManager()
        assert_equal(len(self.a._kernels.keys()), 0)
        assert_equal(len(self.a._comps.keys()), 0)
        assert_equal(len(self.a._clients.keys()),0)
        #context exists

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
        try:
            (b, c) = self.a.get_hb_info("blah")
        except:
            
        


# More needed, this just shows how it can be done
