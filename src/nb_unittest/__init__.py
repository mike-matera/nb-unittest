"""
An IPython plugin that make it possible to write clear, concise and safe unit
tests for student code. Tests run in a context that's protected from common
student errors.
"""

import unittest
from functools import wraps
from typing import Callable, Iterator

from . import tagcache
from .tagcache import assert_error, assert_ok, nbtest_attrs

_cache = None

__all__ = [
    "nbtest_attrs",
    "assert_error",
    "assert_ok",
    "get",
    "items",
    "tags",
    "warning",
    "info",
    "error",
]


def get(tag: str) -> tagcache.TagCacheEntry:
    """
    Retrieve cell information by the tag name. Tag names should include
    the @ symbol.
    """
    if _cache is None:
        raise RuntimeError("The nbtest extension has not been loaded.")
    return _cache._cache[tag]


def items() -> Iterator[tuple[str, tagcache.TagCacheEntry]]:
    """Return an iterator of cell cell tags and cache entries."""
    return _cache._cache.items()


def tags() -> Iterator[str]:
    """Return an iterator of cell tags."""
    return _cache._cache.keys()


def _severity(level: str):
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def _w(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except unittest.case.TestCase.failureException as e:
                e.severity = level
                raise e

        _w.__doc__ = f.__doc__
        return _w

    return decorator


warning = _severity("warning")
warning.__doc__ = (
    """A decorator for test functions that marks a failure as a warning."""
)

error = _severity("error")
error.__doc__ = """A decorator for test functions that marks a failure as an error (the default)."""

info = _severity("info")
info.__doc__ = """A decorator for test functions that marks a failure as an information."""


def load_ipython_extension(ipython):
    global _cache
    _cache = tagcache.TagCache(ipython)
    ipython.register_magics(_cache)
    ipython.events.register("post_run_cell", _cache.post_run_cell)
