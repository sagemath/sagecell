from trusted_kernel_manager import TrustedMultiKernelManager, UntrustedMultiKernelManager
from nose.tools import assert_equal, assert_not_equal, assert_raises, raises

class TestTrustedMultiKernelManager:
    def test_init(self):
        a = TrustedMultiKernelManager()
        assert_equal(len(a._kernels.keys()), 0)


# More needed, this just shows how it can be done
