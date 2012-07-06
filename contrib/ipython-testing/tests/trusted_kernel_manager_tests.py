import trusted_kernel_manager
from nose.tools import *
import random
import os
import sys
import ast
import zmq
from IPython.zmq.session import Session
from contextlib import contextmanager
import time
import misc
import re
import config as conf
sage = conf.sage
configg = misc.Config()
d = configg.get_default_config("_default_config")

from IPython.testing.decorators import skip

# from the attest python package - license is modified BSD
from StringIO import StringIO
@contextmanager
def capture_output(split=False):
    """Captures standard output and error during the context. Returns a
    tuple of the two streams as lists of lines, added after the context has
    executed.

    .. testsetup::

        from attest import capture_output

    >>> with capture_output() as (out, err):
    ...    print 'Captured'
    ...
    >>> out
    ['Captured']

    """
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    out, err = [], []
    try:
        yield out, err
    finally:
        if split:
            out.extend(sys.stdout.getvalue().splitlines())
            err.extend(sys.stderr.getvalue().splitlines())
        else:
            out.append(sys.stdout.getvalue())
            err.append(sys.stderr.getvalue())
        sys.stdout, sys.stderr = stdout, stderr
        
        
  
def test_init():
    tmkm = trusted_kernel_manager.TrustedMultiKernelManager()
    assert_equal(len(tmkm._kernels.keys()), 0)
    assert_equal(len(tmkm._comps.keys()), 0)
    assert_equal(len(tmkm._clients.keys()),0)
    assert_true(hasattr(tmkm, "context"))

  
def test_init_parameters():
    tmkm = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = {"a": "b"}, kernel_timeout = 3.14)
    assert_equal(tmkm.default_computer_config, {"a": "b"})
    assert_equal(tmkm.kernel_timeout, 3.14)

    
class TestTrustedMultiKernelManager(object):
    executing_re = re.compile(r'executing .* -python .*receiver\.py.*/dev/null')
    default_comp_config = {"host": "localhost",
                          "username": None,
                          "python": sage + " -python",
                          "log_file": None,
                          "max": 15}

    def setUp(self): #called automatically before each test is run
        self.a = trusted_kernel_manager.TrustedMultiKernelManager(default_computer_config = d)

    def _populate_comps_kernels(self):
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
            try:
                self.a.remove_computer(i)
            except:
                pass
        
    
    def test_get_kernel_ids_success(self):
        self._populate_comps_kernels()
        x = self.a.get_kernel_ids("testcomp1")
        y = self.a.get_kernel_ids("testcomp2")
        assert_equal(len(x), 2)
        assert_equal(len(y), 1)
        assert_equal("kone" in x, True)
        assert_equal("ktwo" in x, True)
        assert_equal("kthree" in x, False)
        assert_equal("kthree" in y, True)

      
    def test_get_kernel_ids_invalid_comp(self):
        self._populate_comps_kernels()
        x = self.a.get_kernel_ids("testcomp3")
        assert_equal(len(x), 0)
        
      
    def test_get_kernel_ids_no_args(self):
        self._populate_comps_kernels()
        self.a._kernels = {"a": None, "b": None, "c": None}
        x = self.a.get_kernel_ids()
        assert_equal(len(x), 3)

      
    def test_get_hb_info_success(self):
        self._populate_comps_kernels()
        (b, c) = self.a.get_hb_info("kone")
        assert_equal(b, 3.0)
        assert_equal(c, 5.0)
        (b, c) = self.a.get_hb_info("kthree")
        assert_equal(b, 2.0)
        assert_equal(c, 4.0)
        
      
    def test_get_hb_info_invalid_kernel_id(self):
        self._populate_comps_kernels()
        assert_raises(KeyError, self.a.get_hb_info, "blah")

    
    def test_ssh_untrusted(self):
        client = self.a._setup_ssh_connection(self.default_comp_config["host"], self.default_comp_config["username"])
        with capture_output() as (out, err):
            x = self.a._ssh_untrusted(self.default_comp_config, client)
        out = out[0]
        assert_equal(x == None, False)
        assert_equal(len(x), 5)
        assert_is_not_none(self.executing_re.match(out))

    def test_add_computer_success(self): # depends on _setup_ssh_connection, _ssh_untrusted
        new_config = self.default_comp_config.copy()
        new_config.update({'beat_interval': 0.5, 'first_beat': 1, 'kernels': {}})

        with capture_output(split=True) as (out,err):
            x = self.a.add_computer(self.default_comp_config)

        assert_equal(len(str(x)), 36)
        assert_in(x, self.a._comps)
        for k in new_config:
            assert_equal(self.a._comps[x][k], new_config[k], "config value %s (%s) does not agree (should be %s)"%(k,self.a._comps[x][k], new_config[k]))

        #TODO: the following two asserts don't pass...
        #assert_in("socket", self.a._clients[x])
        #assert_equal(self.a._clients[x]["socket"].socket_type, 3)

        assert_in("ssh", self.a._clients[x])

        assert_regexp_matches(out[0], self.executing_re)
        assert_regexp_matches(out[1], r'ZMQ Connection with computer \w+-\w+-\w+-\w+-\w+ at port \d+ established')

    def test_setup_ssh_connection_success(self):
        x = self.a._setup_ssh_connection("localhost", username=None)
        assert_equal("AutoAddPolicy" in str(x._policy), True)
        assert_equal(len(x.get_host_keys()), 1)
    
    def _check_all_kernels_killed_out(self, out):
        expected_out = {'content': {'status': 'All kernels killed!'}, 'type': 'success'}
        outdict = ast.literal_eval(out)
        assert_equal(outdict, expected_out)
        
    def test_purge_kernels_no_kernels(self): # depends on add_computer
        x = self.a.add_computer(self.default_comp_config)

        with capture_output() as (out, err):
            self.a.purge_kernels(x)
        out = out[0]

        self._check_all_kernels_killed_out(out)
        assert_equal(self.a._comps[x]["kernels"], {})
        assert_equal(self.a._kernels, {})

    def test_purge_kernels_success(self): # depends on add_computer, new_session
        x = self.a.add_computer(self.default_comp_config)
        y = self.a.new_session()
        z = self.a.new_session()

        with capture_output() as (out, err):
            self.a.purge_kernels(x)
        out = out[0]
        self._check_all_kernels_killed_out(out)
        assert_equal(self.a._comps[x]["kernels"], {})
        assert_equal(self.a._kernels, {})

    def test_remove_computer_success(self): # depends on add_computer, new_session
        x = self.a.add_computer(self.default_comp_config)
        kern1 = self.a.new_session()
        kern2 = self.a.new_session()
        b = self.a.add_computer(self.default_comp_config)
        
        # remove computer with active kernels
        with capture_output() as (out, err):
                self.a.remove_computer(x)
        out = out[0]
        self._check_all_kernels_killed_out(out)
        assert_not_in(kern1, self.a._kernels)
        assert_not_in(kern2, self.a._kernels)
        assert_not_in(x, self.a._comps)

        # remove computer with no kernels
        with capture_output() as (out, err):
                self.a.remove_computer(b)
        out = out[0]
        self._check_all_kernels_killed_out(out)
        assert_not_in(b, self.a._comps)

    def test_restart_kernel_success(self): # depends on add_computer, new_session
        x = self.a.add_computer(self.default_comp_config)
        kern1 = self.a.new_session()
        kern2 = self.a.new_session()

        with capture_output() as (out, err):
            self.a.restart_kernel(kern2)
        out = out[0]

        y = ast.literal_eval(out)
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
        
    def test_interrupt_kernel_success(self): # depends on add_computer, new_session
        x = self.a.add_computer(self.default_comp_config)
        kern1 = self.a.new_session()

        with capture_output() as (out, err):
            self.a.interrupt_kernel(kern1)
        out = out[0]

        assert_in('interrupted', out)
        assert_not_in('not', out)
        #TODO: there should be a way of detecting if the kernel was interrupted without relying on stdout

    def test_new_session_success(self): # depends on add_computer
        x = self.a.add_computer(self.default_comp_config)

        with capture_output() as (out, err):
            kern1 = self.a.new_session()
        out = out[0]

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

        assert_equal("CONNECTION FILE ::: " in out, True)

    def test_end_session_success(self): # depends on add_computer, new_session
        x = self.a.add_computer(self.default_comp_config)
        kern1 = self.a.new_session()
        kern2 = self.a.new_session()
        with capture_output(split=True) as (out,err):
            self.a.end_session(kern1)

        assert_equal(kern1 not in self.a._kernels.keys(), True)
        for i in self.a._comps.keys():
            assert_not_in(kern1, self.a._comps[i]["kernels"].keys())

        assert_in("Killing Kernel ::: %s at " %kern1, out[0])
        assert_in("Kernel %s successfully killed."% kern1, out[1])
        with capture_output(split=True) as (out,err):
            self.a.end_session(kern2)

        assert_equal(kern2 not in self.a._kernels.keys(), True)
        for k,v in self.a._comps.items():
            assert_not_in(kern2, v["kernels"])

        assert_in("Killing Kernel ::: %s at "%kern2, out[0])
        assert_in("Kernel %s successfully killed."%kern2, out[1])

    def test_find_open_computer_success(self):
        self.a._comps["testcomp1"] = {"max_kernels": 3, "kernels": {}}
        self.a._comps["testcomp2"] = {"max_kernels": 5, "kernels": {}}

        for i in range(8):
            y = self.a._find_open_computer()
            assert_equal(y == "testcomp1" or y == "testcomp2", True)
            self.a._comps[y]["max_kernels"] -= 1

        try:
            self.a._find_open_computer()
        except IOError as e:
            assert_equal("Could not find open computer. There are 2 computers available.", e.message)

    def test_create_connected_stream(self):
        cfg = {"host": "localhost"}
        port = 51337
        socket_type = zmq.SUB

        with capture_output() as (out, err):
            ret = self.a._create_connected_stream(cfg, port, socket_type)
        out = out[0]

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.SUB)

        assert_equal(out, "Connecting to: tcp://%s:%i\n" % (cfg["host"], port))

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
        kernel_id = "kern1"
        comp_id = "testcomp1"
        self.a._kernels[kernel_id] = {"comp_id": comp_id, "connection": {"iopub_port": 50101}}
        self.a._comps[comp_id] = {"host": "localhost"}

        ret = self.a.create_iopub_stream(kernel_id)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.SUB)

    
    def test_create_shell_stream(self): # depends on create_connected_stream
        kernel_id = "kern1"
        comp_id = "testcomp1"
        self.a._kernels[kernel_id] = {"comp_id": comp_id, "connection": {"shell_port": 50101}}
        self.a._comps[comp_id] = {"host": "localhost"}

        ret = self.a.create_shell_stream(kernel_id)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.DEALER)

    
    def test_create_hb_stream(self): # depends on create_connected_stream
        kernel_id = "kern1"
        comp_id = "testcomp1"
        self.a._kernels[kernel_id] = {"comp_id": comp_id, "connection": {"hb_port": 50101}}
        self.a._comps[comp_id] = {"host": "localhost"}

        ret = self.a.create_hb_stream(kernel_id)

        assert_equal(ret.closed(), False)
        assert_equal(ret.socket.socket_type, zmq.REQ)

