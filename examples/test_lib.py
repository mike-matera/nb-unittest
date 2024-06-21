"""
Importable test cases for nbtest
"""

import unittest

from nbtest import nbtest_attrs


class ATestCase(unittest.TestCase):
    """An importable test case."""

    def test_reusable(self):
        self.fail()


class CustomizableTestCase(unittest.TestCase):
    """A test case that is made to be customized."""

    fail_message = "Default failure message."

    def test_customized(self):
        """Just an example of customization."""
        self.fail(self.fail_message)


class DerivedCase1(CustomizableTestCase):
    fail_message = "Failure message customized by inheritance"


def deco(**kwargs):
    def _deco(cls):
        return type(cls.__name__, (cls,), kwargs)

    return _deco


@deco(fail_message="Failure message customized by a decorator.")
class DerivedCase2(CustomizableTestCase):
    pass


def lib_function():
    """A function that returns a test or tests."""
    suite = unittest.TestSuite()
    for attr in nbtest_attrs:

        class _tc(CustomizableTestCase):
            fail_message = f"Customized for attribute {attr}"

        suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(_tc))
    return suite
