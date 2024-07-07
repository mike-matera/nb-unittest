"""
An IPython plugin that make it possible to write clear, concise and safe unit tests for student code.
Tests run in a context that's protected from common student errors.
"""

import ast
import re
import types
import unittest
import sys

from IPython.core.magic import Magics, cell_magic, magics_class
from IPython.display import HTML

from .templ import templ
from .unit import NotebookTestRunner

nbtest_attrs = {}
runner_class = NotebookTestRunner

@magics_class
class CellCache(Magics):
    """
    A stateful cell magic and event handler that maintains a cache of executed
    cells that is used to run unit tests on code in different cells.
    """

    def __init__(self, shell):
        super().__init__(shell)
        self._cache = {}
        self._test_ns = {"shell": self.shell}

    @cell_magic
    def testing(self, line, cell):
        """
        A cell magic that finds and runs unit tests on selected symbols.
        """
        global nbtest_attrs

        self._test_ns["nbtest_cases"] = None
        nbtest_attrs.clear()

        # Find the symbols mentioned in the cell magic
        try:
            for attr, value in (
                (
                    x[1:],
                    self._cache[x],
                )
                if x.startswith("@")
                else (
                    x,
                    self.shell.user_ns[x],
                )
                for x in line.split()
            ):
                self._test_ns[attr] = value
                nbtest_attrs[attr] = value
        except KeyError as e:
            return HTML(templ.missing.render(missing=e))

        # Run the cell
        try:
            tree = ast.parse(cell)
            exec(compile(tree, filename="<testing>", mode="exec"), self._test_ns)
        except AssertionError as e:
            return HTML(templ.assertion.render(error=e))
        
        # Find and execute test cases.
        suite = unittest.TestSuite()

        if self._test_ns["nbtest_cases"] is not None:
            # Test cases are specified
            for tc in self._test_ns["nbtest_cases"]:
                match tc:
                    case str():
                        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(tc))
                    case _ if isinstance(tc, unittest.TestCase) or isinstance(
                        tc, unittest.TestSuite
                    ):
                        suite.addTest(tc)
                    case type() if issubclass(tc, unittest.TestCase):
                        suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(tc))
                    case types.ModuleType():
                        suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(tc))
                    case _:
                        raise ValueError(
                            f"Invalid value in test_cases: {tc}. Entries must be a string, TestCase class or instance, a TestSuite, or a module."
                        )

        else:
            # Look for cases in the cell
            class top_test_visitor(ast.NodeVisitor):
                """Parse the input cell to find top level test class and test function defs"""

                def visit_ClassDef(_, node):
                    if isinstance(self._test_ns[node.name], type) and issubclass(
                        self._test_ns[node.name], unittest.TestCase
                    ):
                        suite.addTest(
                            unittest.defaultTestLoader.loadTestsFromTestCase(
                                self._test_ns[node.name]
                            )
                        )
                    # do not descend

                def visit_FunctionDef(_, node):
                    if node.name.startswith("test") and callable(self._test_ns[node.name]):
                        suite.addTest(unittest.FunctionTestCase(self._test_ns[node.name]))
                    # do not descend

            top_test_visitor().visit(tree)

        # Run tests
        runner = runner_class()
        result = runner.run(suite)
        return HTML(templ.result.render(result=result))

    def post_run_cell(self, result):
        """
        Callback after a cell has run.
        """
        if result.execution_count is not None:
            # Avoid caching on run().
            entry = CacheEntry(result, self.shell)
            for tag in entry.tags:
                self._cache[tag] = entry


class CacheEntry:
    """
    Information about an executed cell.
    """

    def __init__(self, result, shell):
        """Create an entry."""

        self.id = result.info.cell_id
        self.info = result.info
        self.result = result
        self.shell = shell
        self.source = shell.transform_cell(result.info.raw_cell)

        try:
            self.tree = ast.parse(self.source)
            self.docstring = ast.get_docstring(self.tree)
            self.tokens = set((x.__class__ for x in ast.walk(self.tree)))

        except SyntaxError:
            self.tree = None
            self.docstring = None
            self.tokens = None

        if self.docstring is not None:
            self.tags = [
                m.group(1)
                for x in self.docstring.split("\n")
                if (m := re.match(r"(@\S+)", x.strip())) is not None
            ]
        else:
            self.tags = []

    def run(self, push={}, silent=False):
        self.shell.push(push)
        return self.shell.run_cell(self.source, store_history=False, silent=silent).result

