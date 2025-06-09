"""
Simplifications of unittest classes that focus on readable results.
"""

import asyncio
import time
import unittest
from types import TracebackType

try:
    from unittest.case import _addSkip, _Outcome
except ImportError:
    # Python 3.10 compatibility
    import warnings

    def _addSkip(result, test_case, reason):
        addSkip = getattr(result, "addSkip", None)
        if addSkip is not None:
            addSkip(test_case, reason)
        else:
            warnings.warn(
                "TestResult has no addSkip method, skips not reported",
                RuntimeWarning,
                2,
            )
            result.addSuccess(test_case)


class NotebookTestSuite:
    """
    A simplified test suite.
    """

    def __init__(self, tests=()):
        self._tests = list(tests)

    # For compatibility with the default runner.
    def __call__(self, result):
        return self.run(result)

    def addTest(self, test):
        self._tests.append(test)

    def run(self, result):
        for test in self._tests:
            if result.shouldStop:
                return result
            test.run(result)
        return result

    async def async_run(self, result):
        for test in self._tests:
            if result.shouldStop:
                return result
            if isinstance(test, unittest.TestCase):
                await generic_async_run(test, result)
            else:
                await test.async_run(result)
        return result


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
        err: tuple[type[BaseException], BaseException, TracebackType]
        | tuple[None, None, None],
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
        err: tuple[type[BaseException], BaseException, TracebackType]
        | tuple[None, None, None],
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
        err: tuple[type[BaseException], BaseException, TracebackType]
        | tuple[None, None, None],
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

        default_message = """The function <span style="font-family: monospace">{}()</span> reported an error."""

        if test.__class__ == unittest.TestCase:
            return default_message.format(".".join(test.id().split(".")[-2:]))
        else:
            return default_message.format(test.id())

    def _format_error(
        self,
        err: tuple[type[BaseException], BaseException, TracebackType]
        | tuple[None, None, None],
    ) -> str:
        if not issubclass(err[0], AssertionError):
            return f"""{err[0].__name__}: {err[1]}"""
        else:
            return err[1]


class NotebookTestRunner:
    """
    An simple test runner that provides an async run() method.
    """

    async def async_run(self, test: NotebookTestSuite) -> NotebookResult:
        return await test.async_run(NotebookResult())

    def run(self, test: NotebookTestSuite) -> NotebookResult:
        return test.run(NotebookResult())


class AsyncFunctionTestCase(unittest.FunctionTestCase):
    """
    A wrapper for aync functions.
    """

    def __init__(self, testFunc):
        super().__init__(testFunc, setUp=None, tearDown=None, description=None)

    async def runTest(self):
        if asyncio.iscoroutinefunction(self._testFunc):
            return await self._testFunc()
        else:
            return self._testFunc()


async def generic_async_run(self, result):
    """
    An async version of TestCase.run() defined here:
        https://github.com/python/cpython/blob/main/Lib/unittest/case.py

    As Jason Fried said, "The best solution is to provide an entire async call
    chain from their code to your code and maintain a separate blocking chain
    that used to exist."

        https://youtu.be/XW7yv6HuWTE?si=0SV9ISfL2qUH11F7

    Hopefully the unittest library will catch up.
    """

    async def run_or_await(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    stopTestRun = None

    result.startTest(self)
    try:
        testMethod = getattr(self, self._testMethodName)
        if getattr(self.__class__, "__unittest_skip__", False) or getattr(
            testMethod, "__unittest_skip__", False
        ):
            # If the class or method was skipped.
            skip_why = getattr(
                self.__class__, "__unittest_skip_why__", ""
            ) or getattr(testMethod, "__unittest_skip_why__", "")
            _addSkip(result, self, skip_why)
            return result

        expecting_failure = getattr(
            self, "__unittest_expecting_failure__", False
        ) or getattr(testMethod, "__unittest_expecting_failure__", False)
        outcome = _Outcome(result)
        start_time = time.perf_counter()
        try:
            self._outcome = outcome

            with outcome.testPartExecutor(self):
                # self._callSetUp()
                await run_or_await(self.setUp)
            if outcome.success:
                outcome.expecting_failure = expecting_failure
                with outcome.testPartExecutor(self):
                    # self._callTestMethod(testMethod)
                    await run_or_await(testMethod)
                outcome.expecting_failure = False
                with outcome.testPartExecutor(self):
                    # self._callTearDown()
                    await run_or_await(self.tearDown)
            self.doCleanups()

            # XXX: Not until Python 3.12
            # self._addDuration(result, (time.perf_counter() - start_time))

            if outcome.success:
                if expecting_failure:
                    if outcome.expectedFailure:
                        self._addExpectedFailure(
                            result, outcome.expectedFailure
                        )
                    else:
                        self._addUnexpectedSuccess(result)
                else:
                    result.addSuccess(self)
            return result
        finally:
            # explicitly break reference cycle:
            # outcome.expectedFailure -> frame -> outcome -> outcome.expectedFailure
            outcome.expectedFailure = None
            outcome = None

            # clear the outcome, no more needed
            self._outcome = None

    finally:
        result.stopTest(self)
        if stopTestRun is not None:
            stopTestRun()
