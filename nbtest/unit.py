"""
Simplifications of unittest classes that focus on readable results.
"""

import unittest
from types import TracebackType


class NotebookTestRunner:
    """
    An simple test runner that provides verbose results and captures output.
    """

    def run(self, test: unittest.TestSuite | unittest.TestCase) -> unittest.TestResult:
        return test.run(NotebookResult())


class NotebookResult(unittest.TestResult):
    """
    An implementation of unittest.TestResult
    """

    def __init__(self) -> None:
        super().__init__(None, None, None)
        self.successes = []

    def addError(
        self,
        test: unittest.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        self.stop()
        self.errors.append(
            (
                self._format_test_name(test),
                self._format_error(err),
            )
        )

    def addFailure(
        self,
        test: unittest.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        self.stop()
        self.failures.append(
            (
                self._format_test_name(test),
                self._format_error(err),
            )
        )

    def addSuccess(self, test: unittest.TestCase) -> None:
        self.successes.append(self._format_test_name(test))

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        self.skipped.append(
            (
                self._format_test_name(test),
                reason,
            )
        )

    def addExpectedFailure(
        self,
        test: unittest.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        self.expectedFailures.append(
            self._format_test_name(test),
            self._format_error(err),
        )

    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        self.stop()
        self.unexpectedSuccesses.append(self._format_test_name(test))

    def _format_test_name(self, test: unittest.TestCase) -> str:
        # Getting unfiltered information from unittest isn't possible. Ugh.
        if test.__class__ == unittest.FunctionTestCase:
            desc = test._testFunc.__doc__
        elif test.__class__ == unittest.TestCase:
            desc = test._testMethodDoc
        else:
            desc = test.shortDescription()

        if desc is not None:
            return desc.strip()

        default_message = (
            """The function <span style="font-family: monospace">{}()</span> reported an error."""
        )

        if test.__class__ == unittest.TestCase:
            return default_message.format(".".join(test.id().split(".")[-2:]))
        else:
            return default_message.format(test.id())

    def _format_error(
        self,
        err: tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None],
    ) -> str:
        if not issubclass(err[0], AssertionError):
            return f"""{err[0].__name__}: {err[1]}"""
        else:
            return err[1]
