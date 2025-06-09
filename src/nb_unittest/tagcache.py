"""
The implementation of a cell tag cache.
"""

import ast
import asyncio
import io
import re
import sys
import types
import unittest
from dataclasses import dataclass
from typing import Any, Mapping, Set, Union

import IPython.core.ultratb
import ipywidgets
from IPython.core.interactiveshell import ExecutionResult, InteractiveShell
from IPython.core.magic import Magics, cell_magic, magics_class
from IPython.display import HTML

from .analysis import AnalysisNode
from .templ import templ
from .transforms import RewriteVariableAssignments
from .unit import AsyncFunctionTestCase, NotebookTestRunner, NotebookTestSuite

nbtest_attrs = {}
runner_class = NotebookTestRunner
_last_succeeded = None
_last_error = None


def assert_error():
    """
    Return an exception if the last test run failed or None if it succeeded,
    reverse if success is True.
    """
    global _last_error
    if _last_error is None:
        raise RuntimeError("ERROR: pass instead of fail.")


def assert_ok():
    """
    Return an exception if the last test run failed or None if it succeeded,
    reverse if success is True.
    """
    global _last_error
    if _last_error is not None:
        raise _last_error


@dataclass
class CellRunResult:
    """The result of calling run() on a TagCacheEntry"""

    stdout: str
    stderr: str
    outputs: list[Any]
    result: Any


@magics_class
class TagCache(Magics):
    """
    A stateful cell magic and event handler that maintains a cache of executed
    cells that is used to run unit tests on code in different cells.
    """

    def __init__(self, shell: InteractiveShell):
        """Initialize the plugin."""
        super().__init__(shell)
        self._cache = {}
        self._test_ns = {"shell": self.shell}

    @cell_magic
    def testing(self, line: str, cell: str) -> HTML:
        """
        A cell magic that finds and runs unit tests on selected symbols.
        """
        global nbtest_attrs, _last_error, _last_succeeded

        _last_succeeded = False
        _last_error = None

        self._test_ns["nbtest_cases"] = None
        nbtest_attrs.clear()

        # Find extended symbols mentioned in the cell magic
        if line.strip() != "":
            try:
                for s in (x.strip() for x in line.split(",")):
                    if m := re.match(r"^(\S+)\s+as\s+(\S+)$", s):
                        symbol = m.group(1)
                        target = m.group(2)

                        if symbol.startswith("@"):
                            value = self._cache[symbol]
                        else:
                            value = self.shell.user_ns[symbol]

                    elif m := re.match(r"^(\S+)$", s):
                        symbol = m.group(1)

                        if symbol.startswith("@"):
                            value = self._cache[symbol]
                            target = symbol[1:]
                        else:
                            value = self.shell.user_ns[symbol]
                            target = symbol

                    else:
                        raise ValueError(
                            f"""Bad identifier "{s}". Did you use commas to separate identifiers?"""
                        )

                    self._test_ns[target] = value
                    nbtest_attrs[target] = value

            except KeyError as e:
                _last_error = e
                return HTML(templ.missing.render(missing=e))

        # Run the cell
        try:
            tree = ast.parse(cell)
            exec(
                compile(tree, filename="<testing>", mode="exec"), self._test_ns
            )
        except AssertionError as e:
            _last_error = e
            return HTML(templ.assertion.render(error=e))

        # Look for async test cases.
        do_async = False
        funct_testcase = unittest.FunctionTestCase

        class async_visitor(ast.NodeVisitor):
            def visit_AsyncFunctionDef(_, node):
                nonlocal funct_testcase, do_async
                do_async = True
                funct_testcase = AsyncFunctionTestCase

        async_visitor().visit(tree)

        # Find and execute test cases.
        suite = NotebookTestSuite()
        loader = unittest.TestLoader()
        loader.suiteClass = NotebookTestSuite

        if self._test_ns["nbtest_cases"] is not None:
            # Test cases are specified
            for tc in self._test_ns["nbtest_cases"]:
                if isinstance(tc, str):
                    suite.addTest(loader.loadTestsFromName(tc))
                elif isinstance(tc, unittest.TestCase) or isinstance(
                    tc, unittest.TestSuite
                ):
                    suite.addTest(tc)
                elif isinstance(tc, type) and issubclass(
                    tc, unittest.TestCase
                ):
                    suite.addTest(loader.loadTestsFromTestCase(tc))
                elif isinstance(tc, types.ModuleType):
                    suite.addTest(loader.loadTestsFromModule(tc))
                elif isinstance(tc, types.FunctionType):
                    suite.addTest(funct_testcase(tc))
                else:
                    raise ValueError(f"""Invalid value in test_cases: {tc}.""")

        else:
            # Look for cases in the cell
            class top_test_visitor(ast.NodeVisitor):
                """Parse the input cell to find top level test class and test function defs"""

                def visit_ClassDef(_, node):
                    if isinstance(
                        self._test_ns[node.name], type
                    ) and issubclass(
                        self._test_ns[node.name], unittest.TestCase
                    ):
                        suite.addTest(
                            loader.loadTestsFromTestCase(
                                self._test_ns[node.name]
                            )
                        )
                    # do not descend

                def visit_FunctionDef(_, node):
                    if node.name.startswith("test") and callable(
                        self._test_ns[node.name]
                    ):
                        suite.addTest(funct_testcase(self._test_ns[node.name]))
                    # do not descend

                def visit_AsyncFunctionDef(_, node):
                    if node.name.startswith("test") and callable(
                        self._test_ns[node.name]
                    ):
                        suite.addTest(funct_testcase(self._test_ns[node.name]))
                    # do not descend

            top_test_visitor().visit(tree)

        if do_async:
            # Asynchronous execution. This has some problems.

            output = ipywidgets.Output()
            html = ipywidgets.HTML(templ.wait.render())
            output.append_display_data(html)

            async def do_run():
                global _last_error
                nonlocal output
                try:
                    with output:
                        runner = runner_class()
                        result = await runner.async_run(suite)
                        html.value = templ.result.render(result=result)
                        if result.wasSuccessful():
                            _last_error = None
                        else:
                            _last_error = RuntimeError("An aync test failed.")

                except Exception as e:
                    _last_error = e
                    formatter = IPython.core.ultratb.AutoFormattedTB(
                        mode="Verbose", color_scheme="Linux"
                    )
                    output.append_stderr(formatter.text(*sys.exc_info()))

            asyncio.create_task(do_run(), name="Test Runner")
            return output

        else:
            # Synchronous execution.
            runner = runner_class()
            result = runner.run(suite)
            if result.wasSuccessful():
                _last_error = None
            else:
                _last_error = RuntimeError("A test failed.")
            return HTML(templ.result.render(result=result))

    def post_run_cell(self, result):
        """
        Callback after a cell has run.
        """
        if result.execution_count is not None:
            # Avoid caching on run().
            entry = TagCacheEntry(result, self.shell)
            for tag in entry.tags:
                self._cache[tag] = entry


class TagCacheEntry(AnalysisNode):
    """
    Information about an executed cell.
    """

    def __init__(self, result, shell):
        """Create an entry."""

        self._id = result.info.cell_id
        self._result = result
        self._shell = shell
        self._tags = []

        try:
            source = shell.transform_cell(result.info.raw_cell)
            super().__init__(source)
            if self.docstring is not None:
                self._tags = [
                    m.group(1)
                    for x in self.docstring.split()
                    if (m := re.match(r"(@\S+)", x)) is not None
                ]
        except SyntaxError:
            super().__init__(None, None)

    @property
    def id(self) -> str:
        """The unique identifier of the notebook cell."""
        return self._id

    @property
    def result(self) -> ExecutionResult:
        """The ExecutionResult from running the cell in IPython."""
        return self._result

    @property
    def tags(self) -> Set[str]:
        """A set of the tags found in the cell."""
        return set(self._tags)

    @property
    def ns(self) -> Mapping:
        return self._shell.user_ns

    def run(
        self, push: Mapping = {}, capture: bool = True
    ) -> Union[CellRunResult, None]:
        """
        Run the contents of a cached cell.

        push: Update variables in the notebook namespace with names and values
            in `push` before running the contents.
        capture: Set to `True` (the default) to capture stdout, stderr and
            output. If `False` run() returns `None`
        """
        self._shell.push(push)
        try:
            save_out = sys.stdout
            save_err = sys.stderr
            save_idh = sys.displayhook
            save_edh = self._shell.user_ns["__builtins__"].display

            out = io.StringIO()
            err = io.StringIO()
            outputs = []
            result = None

            def explicit_displayhook(obj):
                nonlocal outputs
                if obj is not None:
                    outputs.append(obj)

            def implicit_displayhook(obj):
                nonlocal result, explicit_displayhook
                explicit_displayhook(obj)
                result = obj

            if capture:
                sys.stdout = out
                sys.stderr = err
                sys.displayhook = implicit_displayhook
                self._shell.user_ns[
                    "__builtins__"
                ].display = explicit_displayhook

            transformer = RewriteVariableAssignments(*list(push.keys()))
            self._shell.ast_transformers.append(transformer)
            self._shell.run_cell(
                self.source, store_history=False, silent=False
            )

            if capture:
                return CellRunResult(
                    stdout=out.getvalue(),
                    stderr=err.getvalue(),
                    outputs=outputs,
                    result=result,
                )
            else:
                return None

        finally:
            sys.stdout = save_out
            sys.stderr = save_err
            sys.displayhook = save_idh
            self._shell.user_ns["__builtins__"].display = save_edh
            self._shell.ast_transformers.remove(transformer)
