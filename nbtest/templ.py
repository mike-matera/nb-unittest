"""
Template configuration for nbtest
"""

from jinja2 import Environment, PackageLoader, Template, select_autoescape


class _Templates:
    """Manage templates used by nbtest."""

    def __init__(self):
        self._env = Environment(loader=PackageLoader("nbtest"), autoescape=select_autoescape())
        self.assertion = "assertion.html"
        self.fail = "fail.html"
        self.missing = "missing.html"
        self.ok = "ok.html"

    def _load(self, value):
        if isinstance(value, Template):
            return value
        else:
            # Assume file name
            return self._env.get_template(value)

    @property
    def assertion(self):
        return self._assertion

    @assertion.setter
    def assertion(self, value):
        self._assertion = self._load(value)

    @property
    def fail(self):
        return self._fail

    @fail.setter
    def fail(self, value):
        self._fail = self._load(value)

    @property
    def missing(self):
        return self._missing

    @missing.setter
    def missing(self, value):
        self._missing = self._load(value)

    @property
    def ok(self):
        return self._ok

    @ok.setter
    def ok(self, value):
        self._ok = self._load(value)


# Singleton instance.
templ = _Templates()
