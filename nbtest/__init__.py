"""
An IPython plugin that make it possible to write clear, concise and safe unit tests for student code.
Tests run in a context that's protected from common student errors.
"""

import unittest
from typing import Iterator

from .tagcache import TagCache, TagCacheEntry, nbtest_attrs

_cache = None

__all__ = ["nbtest_attrs", "get", "items", "tags", "warning", "info", "error"]


def get(tag: str) -> TagCacheEntry:
    if _cache is None:
        raise RuntimeError("The nbtest extension has not been loaded.")
    return _cache._cache[tag]


def items() -> Iterator[tuple[str, TagCacheEntry]]:
    return _cache._cache.items()


def tags() -> Iterator[str]:
    return _cache._cache.keys()


def _severity(level: str):
    def _s(f):
        def _w(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except unittest.case.TestCase.failureException as e:
                e.severity = level
                raise e

        _w.__doc__ = f.__doc__
        return _w

    return _s


warning = _severity("warning")
error = _severity("error")
info = _severity("info")


def load_ipython_extension(ipython):
    global _cache
    _cache = TagCache(ipython)
    ipython.register_magics(_cache)
    ipython.events.register("post_run_cell", _cache.post_run_cell)
