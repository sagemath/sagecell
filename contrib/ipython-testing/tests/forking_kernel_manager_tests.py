import forking_kernel_manager
from misc import assert_is, assert_equal, assert_in, assert_not_in, assert_raises, assert_regexp_matches, assert_is_instance, assert_is_not_none, assert_greater, assert_len, assert_uuid, capture_output
from multiprocessing import Process, Pipe
from IPython.config.loader import Config

def test_init():
    fkm = forking_kernel_manager.ForkingKernelManager("testing.log", '127.0.0.1', update_function=test_init)
    assert_len(fkm.kernels, 0)
    assert_equal(fkm.filename, "testing.log")
    assert_in("function test_init at ", repr(fkm.update_function))

class TestForkingKernelManager(object):
    def setup(self):
        self.a = forking_kernel_manager.ForkingKernelManager("/dev/null", '127.0.0.1', update_function=None)
    def teardown(self):
        for i in self.a.kernels.keys():
            self.a.kernels[i][0].terminate()
    def test_start_kernel_success(self):
        y = self.a.start_kernel()

        assert_is_instance(y, dict)
        assert_len(y, 2)
        assert_in("kernel_id", y)
        assert_uuid(y["kernel_id"])
        assert_in("connection", y)
        assert_len(y["connection"], 6)
        for s in ("stdin_port", "hb_port", "shell_port", "iopub_port"):
            assert_in(s, y["connection"])
            assert_len(str(y["connection"][s]), 5)
        assert_in("ip", y["connection"])
        assert_equal(y["connection"]["ip"], "127.0.0.1")
        assert_in("key", y["connection"])
        assert_uuid(y["connection"]["key"])

        assert_in(y["kernel_id"], self.a.kernels.keys())
        assert_is_instance(self.a.kernels[y["kernel_id"]][0], Process)
        assert_is(self.a.kernels[y["kernel_id"]][0].is_alive(), True)

    def test_resource_limit_setting(self): # incomplete
        y = self.a.start_kernel(resource_limits = {"RLIMIT_CPU": 3})
        proc = self.a.kernels[y["kernel_id"]][0]
        # how to test if rlimit_cpu/any other rlimit is set given the multiprocessing.Process object proc??

    def test_kill_kernel_success(self): # depends on start_kernel
        y = self.a.start_kernel()
        kernel_id = y["kernel_id"]
        proc = self.a.kernels[kernel_id][0]

        assert_is(proc.is_alive(), True)
        retval = self.a.kill_kernel(kernel_id)
        assert_is(retval, True)
        assert_not_in(kernel_id, self.a.kernels.keys())
        assert_is(proc.is_alive(), False)

    def test_kill_kernel_invalid_kernel_id(self):
        kernel_id = 44
        retval = self.a.kill_kernel(kernel_id)
        assert_is(retval, False)

    def test_interrupt_kernel_success(self): # depends on start_kernel
        y = self.a.start_kernel()
        kernel_id = y["kernel_id"]
        proc = self.a.kernels[kernel_id][0]

        assert_is(proc.is_alive(), True)
        retval = self.a.interrupt_kernel(kernel_id)
        assert_is(retval, True)
        assert_is(proc.is_alive(), True)

    def test_interrupt_kernel_invalid_kernel_id(self):
        kernel_id = 44
        retval = self.a.interrupt_kernel(kernel_id)
        assert_is(retval, False)

    def test_restart_kernel_success(self): # depends on start_kernel
        y = self.a.start_kernel()
        kernel_id = y["kernel_id"]
        proc = self.a.kernels[kernel_id][0]
        preports = self.a.kernels[kernel_id][1]

        assert_is(proc.is_alive(), True)
        retval = self.a.restart_kernel(kernel_id)
        assert_is(proc.is_alive(), False) # old kernel process is killed

        proc = self.a.kernels[kernel_id][0]
        assert_is(proc.is_alive(), True) # and a new kernel process with the same kernel_id exists
        postports = self.a.kernels[kernel_id][1]

        for s in ("stdin_port", "hb_port", "shell_port", "iopub_port"):
            assert_equal(preports[s], postports[s]) # and that it has the same ports as before
