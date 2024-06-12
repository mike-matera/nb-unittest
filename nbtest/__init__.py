from . import cache


def find(tag: str) -> cache.CacheEntry:
    if _cache is None:
        raise RuntimeError("The nbtest extension has not been loaded.")
    return _cache._cache[tag]


def load_ipython_extension(ipython):
    global _cache
    _cache = cache.TestCache(ipython)
    ipython.register_magics(_cache)
    ipython.events.register("post_run_cell", _cache.post_run_cell)


_cache = None
