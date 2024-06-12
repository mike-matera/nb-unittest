"""
Simplifications of unittest classes that focus on readable results.
"""

import contextlib
import io
import unittest
from types import TracebackType
from typing import override


class NotebookTestRunner:
    """
    An simple test runner that provides verbose results and captures output.
    """

    def run(self, test: unittest.TestSuite | unittest.TestCase) -> unittest.TestResult:
        with contextlib.redirect_stdout(io.StringIO()) as self.stdout:
            return test.run(NotebookResult())


class NotebookResult(unittest.TestResult):
    """
    An implementation of unittest.TestResult
    """

    @override
    def __init__(self) -> None:
        super().__init__(None, None, None)
        self.successes = []

    @override
    def addError(
        self,
        test: unittest.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        self.errors.append(
            (
                self._format_test_name(test),
                self._format_error(err),
            )
        )

    @override
    def addFailure(
        self,
        test: unittest.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        self.failures.append(
            (
                self._format_test_name(test),
                self._format_error(err),
            )
        )

    @override
    def addSuccess(self, test: unittest.TestCase) -> None:
        self.successes.append(self._format_test_name(test))

    @override
    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        self.skipped.append(
            (
                self._format_test_name(test),
                reason,
            )
        )

    @override
    def addExpectedFailure(
        self,
        test: unittest.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        self.expectedFailures.append(
            self._format_test_name(test),
            self._format_error(err),
        )

    @override
    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        self.unexpectedSuccesses.append(self._format_test_name(test))

    def _format_test_name(self, test: unittest.TestCase) -> str:
        desc = test.shortDescription()
        if desc is not None:
            return desc

        default_message = (
            """The function <span style="font-family: monospace">{}()</span> reported an error."""
        )
        if isinstance(test, unittest.FunctionTestCase):
            return default_message.format(test.id())
        else:
            return default_message.format(".".join(test.id().split(".")[-2:]))

    def _format_error(
        self,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> str:
        if not issubclass(err[0], AssertionError):
            return f"""{err[0].__name__}: {err[1]}"""
        else:
            return err[1]
