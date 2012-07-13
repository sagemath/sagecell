import untrusted_kernel_manager

from misc import assert_is, assert_equal, assert_in, assert_not_in, assert_raises, assert_regexp_matches, assert_is_instance, assert_is_not_none, assert_greater, assert_len, assert_uuid, capture_output, Config

def test_init():
    umkm = untrusted_kernel_manager.UntrustedMultiKernelManager("testing.log", update_function=test_init)
    assert_len(umkm._kernels, 0)
    assert_equal(umkm.filename, "testing.log")
    assert_is(hasattr(umkm, "fkm"), True)

class TestUntrustedMultiKernelManager(object):
    def setup(self):
        self.a = untrusted_kernel_manager.UntrustedMultiKernelManager("/dev/null")
    def teardown(self):
        for i in list(self.a._kernels):
            self.a.kill_kernel(i)

    def test_start_kernel_success(self):
        y = self.a.start_kernel()
        assert_is_instance(y, dict)
        assert_len(y, 2)
        assert_in("kernel_id", y)
        assert_uuid(y["kernel_id"])
        assert_in(y["kernel_id"], self.a._kernels)
        assert_in("connection", y)
        assert_len(y["connection"], 6)
        for s in ("stdin_port", "hb_port", "shell_port", "iopub_port"):
            assert_in(s, y["connection"])
            assert_len(str(y["connection"][s]), 5)
        assert_in("ip", y["connection"])
        assert_equal(y["connection"]["ip"], "127.0.0.1")
        assert_in("key", y["connection"])
        assert_uuid(y["connection"]["key"])

    def test_kill_kernel_success(self): # depends on start_kernel
        y = self.a.start_kernel()
        kernel_id = y["kernel_id"]
        assert_in(kernel_id, self.a._kernels)

        retval = self.a.kill_kernel(kernel_id)
        assert_is(retval, True)
        assert_not_in(kernel_id, self.a._kernels)

    def test_kill_kernel_invalid_kernel_id(self):
        retval = self.a.kill_kernel(44)
        assert_is(retval, False)

    def test_purge_kernels_success(self): # depends on start_kernel
        for i in xrange(5):
            self.a.start_kernel()

        retval = self.a.purge_kernels()
        assert_equal(retval, [])

    def test_purge_kernels_with_failures(self): # depends on start_kernel
        for i in xrange(5):
            self.a.start_kernel()
        self.a._kernels.add(55)
        self.a._kernels.add(66)

        retval = self.a.purge_kernels()
        assert_in(55, retval)
        assert_in(66, retval)
        assert_len(retval, 2)
