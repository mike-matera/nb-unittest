"""
Importable test cases for nbtest
"""

import unittest

from nbtest.cache import nbtest_attrs


class ImportableClass(unittest.TestCase):
    """An importable test case."""

    def test_reusable(self):
        """This is a test case in a reusable test."""
        for attr in nbtest_attrs:
            assert False, f"Just testing for now: {attr}"
