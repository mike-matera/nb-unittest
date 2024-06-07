import sys

from . import magic


def load_ipython_extension(ipython):
    ts = magic.TestCache(ipython)
    ipython.register_magics(ts)
    ipython.events.register("post_run_cell", ts.post_run_cell)
