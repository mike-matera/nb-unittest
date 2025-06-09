"""
Template configuration for nbtest
"""

from jinja2 import Environment, PackageLoader, Template, select_autoescape


class _Templates:
    """Manage templates used by nbtest."""

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("nb_unittest"), autoescape=select_autoescape()
        )

    def _load(self, value):
        if isinstance(value, Template):
            return value
        else:
            # Assume file name in this package.
            return self._env.get_template(value)

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, value):
        self._env = value
        # Load templates using self._env
        self.missing = "missing.html"
        self.assertion = "assertion.html"
        self.result = "result.html"
        self.wait = "wait.html"

    @property
    def assertion(self):
        return self._assertion

    @assertion.setter
    def assertion(self, value):
        self._assertion = self._load(value)

    @property
    def missing(self):
        return self._missing

    @missing.setter
    def missing(self, value):
        self._missing = self._load(value)

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = self._load(value)

    @property
    def wait(self):
        return self._wait

    @wait.setter
    def wait(self, value):
        self._wait = self._load(value)


# Singleton instance.
templ = _Templates()
