"""Tests for kernel provider configuration."""

import unittest

from IPython.core.interactiveshell import InteractiveShell

import kernel_provider


class KernelConfigTests(unittest.TestCase):
    def test_disables_persistent_history_and_sets_kernel_ip(self):
        config = kernel_provider.kernel_config("192.0.2.10")

        self.assertFalse(config.HistoryManager.enabled)
        self.assertEqual(config.IPKernelApp.ip, "192.0.2.10")

    def test_keeps_live_namespace_and_in_memory_history(self):
        shell = InteractiveShell(
            config=kernel_provider.kernel_config("127.0.0.1"))
        try:
            shell.run_cell("linked_value = 41", store_history=True)
            shell.run_cell("linked_value += 1", store_history=True)

            self.assertEqual(shell.user_ns["linked_value"], 42)
            self.assertEqual(shell.history_manager.input_hist_raw[-2:], [
                "linked_value = 41",
                "linked_value += 1",
            ])
            self.assertIsNone(shell.history_manager.save_thread)
        finally:
            InteractiveShell.clear_instance()


if __name__ == "__main__":
    unittest.main()
