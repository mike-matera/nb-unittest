"""
An IPython plugin that make it possible to write clear, concise and safe unit tests for student code.
Tests run in a context that's protected from common student errors.
"""

import ast
import re
import unittest

from IPython.core.magic import Magics, cell_magic, magics_class
from IPython.display import HTML

from .templ import templ
from .unit import NotebookTestRunner

nbtest_attrs = []
runner_class = NotebookTestRunner


@magics_class
class TestCache(Magics):
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
        nbtest_attrs = []

        # Find the symbols mentioned in the cell magic
        try:
            for symbol in (x.strip() for x in line.split()):
                if symbol.startswith("@"):
                    self._test_ns[symbol[1:]] = self._cache[symbol]
                    nbtest_attrs.append(symbol[1:])
                else:
                    self._test_ns[symbol] = self.shell.user_ns[symbol]
                    nbtest_attrs.append(symbol)
        except KeyError as e:
            return HTML(templ.missing.render(error=e))

        # Run the cell
        try:
            tree = ast.parse(cell)
            exec(compile(tree, filename="<testcell>", mode="exec"), self._test_ns)
        except AssertionError as e:
            return HTML(templ.assertion.render(error=e))

        # Find and execute test cases.
        suite = unittest.TestSuite()

        if self._test_ns["nbtest_cases"] is not None:
            # Test cases are specified
            for case in self._test_ns["nbtest_cases"]:
                if isinstance(case, type) and issubclass(case, unittest.TestCase):
                    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(case))
                elif callable(case):
                    for gen_case in case():
                        if isinstance(gen_case, type) and issubclass(gen_case, unittest.TestCase):
                            suite.addTest(
                                unittest.defaultTestLoader.loadTestsFromTestCase(gen_case)
                            )
                        elif isinstance(gen_case, unittest.TestCase):
                            suite.addTest(gen_case)
                elif isinstance(
                    case, re.__class__
                ):  # Couldn't figure out how to reference module class
                    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(case))
                else:
                    raise ValueError(
                        f"Invalid value in test_cases: {case}. Entries must be a unittest.TestCase, a function that returns a list of TestCases or a module."
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

        runner = runner_class()
        result = runner.run(suite)
        if result.wasSuccessful():
            return HTML(templ.ok.render(result=result))
        else:
            return HTML(templ.fail.render(result=result))

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
