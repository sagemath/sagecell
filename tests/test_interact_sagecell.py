import contextlib
import sys
import types
import unittest
from unittest import mock


# interact_sagecell only needs this Sage decorator while it is imported. Keep
# these tests runnable outside a full Sage installation as well as inside one.
try:
    import sage.misc.decorators  # noqa: F401
except ModuleNotFoundError:
    sage = types.ModuleType("sage")
    sage.__path__ = []
    sage_misc = types.ModuleType("sage.misc")
    sage_misc.__path__ = []
    sage_decorators = types.ModuleType("sage.misc.decorators")

    def decorator_defaults(function):
        def wrapper(*args, **kwargs):
            if not kwargs and len(args) == 1:
                return function(*args)
            return lambda f: function(f, *args, **kwargs)
        return wrapper

    sage_decorators.decorator_defaults = decorator_defaults
    sys.modules.update({
        "sage": sage,
        "sage.misc": sage_misc,
        "sage.misc.decorators": sage_decorators,
    })

try:
    import sage.all  # noqa: F401
    HAVE_SAGE = True
except (ImportError, ModuleNotFoundError):
    HAVE_SAGE = False

import interact_sagecell
import interact_compatibility


class FakeControl:
    def __init__(self, value):
        self.value = value
        self.label = None
        self.update = False
        self.adapter = lambda value: value

    def message(self):
        return {}

    def reset(self):
        pass


class FakeSage:
    def __init__(self):
        self.messages = []

    def clear(self, changed):
        pass

    def display_message(self, message):
        self.messages.append(message)

    def reset_kernel_timeout(self, timeout):
        pass


@contextlib.contextmanager
def session_metadata(metadata):
    yield


def automatic_control(control, var=None):
    if isinstance(control, FakeControl):
        return control
    return FakeControl(control)


class InteractSignatureTests(unittest.TestCase):
    def setUp(self):
        interact_sagecell.__dict__["__interacts"].clear()
        self.sage = FakeSage()
        self.patches = [
            mock.patch.object(sys, "_sage_", self.sage, create=True),
            mock.patch.object(
                interact_sagecell, "automatic_control", automatic_control),
            mock.patch.object(
                interact_sagecell, "session_metadata", session_metadata),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()

    def test_explicit_controls_are_passed_through_kwargs(self):
        calls = []

        def f(**kwargs):
            calls.append(kwargs)

        proxy = interact_sagecell.interact(
            controls=[("button", FakeControl("clicked"))])(f)

        self.assertEqual(calls, [{"button": "clicked"}])
        self.assertEqual(proxy._state(), {"button": "clicked"})

    def test_proxy_parameter_is_not_required_for_kwargs(self):
        calls = []

        def f(proxy, **kwargs):
            calls.append((proxy, kwargs))

        proxy = interact_sagecell.interact(
            controls=[("button", FakeControl("clicked"))])(f)

        self.assertIs(calls[0][0], proxy)
        self.assertEqual(calls[0][1], {"button": "clicked"})
        self.assertNotIn("kwargs", proxy._state())

    def test_default_parameters_and_explicit_controls_can_be_combined(self):
        calls = []

        def f(multiplier=2, **kwargs):
            calls.append((multiplier, kwargs))

        proxy = interact_sagecell.interact(
            controls=[("value", FakeControl(3))])(f)

        self.assertEqual(calls, [(2, {"value": 3})])
        self.assertEqual(proxy._state(), {"multiplier": 2, "value": 3})


class InteractControlLayoutTests(unittest.TestCase):
    def test_selector_allows_a_partially_filled_final_row(self):
        control = interact_sagecell.Selector(
            list(range(100)), selector_type="button", nrows=3)

        self.assertEqual((control.nrows, control.ncols), (3, 34))

    def test_button_bar_allows_a_partially_filled_final_row(self):
        control = interact_sagecell.ButtonBar(
            values=list(range(100)), ncols=3)

        self.assertEqual((control.nrows, control.ncols), (34, 3))

    def test_compatibility_selector_uses_buttons_when_rows_are_given(self):
        control = interact_compatibility.selector([1, 2, 3], nrows=2)

        self.assertEqual(control.selector_type, "button")
        self.assertEqual((control.nrows, control.ncols), (2, 2))

    def test_button_layout_rejects_nonpositive_dimensions(self):
        with self.assertRaisesRegex(ValueError, "nrows must be a positive integer"):
            interact_sagecell.Selector(
                [1, 2, 3], selector_type="button", nrows=-2)
        with self.assertRaisesRegex(ValueError, "ncols must be a positive integer"):
            interact_sagecell.ButtonBar(values=[1, 2, 3], ncols=0)

    def test_button_layout_rejects_noninteger_dimensions(self):
        with self.assertRaisesRegex(TypeError, "nrows must be a positive integer"):
            interact_sagecell.Selector(
                [1, 2, 3], selector_type="button", nrows=1.5)

    def test_button_layout_rejects_an_undersized_explicit_grid(self):
        with self.assertRaisesRegex(ValueError, "2 by 2 grid cannot hold 5 buttons"):
            interact_sagecell.ButtonBar(
                values=[1, 2, 3, 4, 5], nrows=2, ncols=2)


@unittest.skipUnless(HAVE_SAGE, "requires SageMath")
class InteractSageIntegrationTests(unittest.TestCase):
    def setUp(self):
        interact_sagecell.__dict__["__interacts"].clear()
        self.sage = FakeSage()
        self.patches = [
            mock.patch.object(sys, "_sage_", self.sage, create=True),
            mock.patch.object(
                interact_sagecell, "session_metadata", session_metadata),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()

    def test_explicit_button_is_passed_through_kwargs(self):
        calls = []

        def f(**kwargs):
            calls.append(kwargs)

        proxy = interact_sagecell.interact(
            controls=[("button", interact_sagecell.Button(value="clicked"))]
        )(f)

        self.assertEqual(calls, [{"button": ""}])
        self.assertEqual(proxy._state(), {"button": False})


if __name__ == "__main__":
    unittest.main()
