# Notebook Embedded Unit Tests 

I distribute graded and ungraded assignments in my [Python Programming for
Everyone](https://github.com/mike-matera/python-for-everyone) class as [Jupyter
Notebooks](https://jupyter.org/). Students download and submit notebooks on
[Canvas LMS](https://www.instructure.com/canvas). When I first started teaching
with Jupyter most students attended class in person. Since the pandemic most
students are full remote. The purpose of this module is to provide a foundation
for checking and grading notebooks that gives helpful and beautiful feedback
when a solution is wrong so that remote students have a better experience. 

The goals of this project are: 

1. To provide a way to reference, analyze and run the contents of an arbitrary
   cell in a notebook.
1. To provide an environment to easily write and run unit tests based on
   Python's `unittest` library.
1. To be lightweight and flexible.

The implementation is an IPython extension that enables cell tagging using
docstrings and implements the `%%testing` cell magic that expects cells that
contain unit tests. 

## Getting Started 

You install `nbtest` using `pip`:

```console 
$ pip install https://github.com/mike-matera/nbtest.git
```

The extension has be be loaded using the `%load_ext` magic before any cell tags
will be remembered: 

```python 
%load_ext nbtest
```

Then subsequent cells can be tagged:

```python
"""@hello"""
print("Hello World")
```

Tagged cells can be easily accessed:


```python 
import nbtest
hello = nbtest.get("@hello")
hello.run()
```

The [examples](examples) directory has notebooks with examples for how to use
each of the features of `nbtest`. 

## Tagging Cells 

One major missing feature of Juptyer is the ability to introspect a notebook.
While it's possible to find a cell by tag in the JavaScript frontend, there is
not currently a way to do that in the Python kernel. This notebook extension
watches cell executions and scans for tags in a cell's docstring. 

Cell tags start with the `@` symbol and appear anywhere in the docstring. Cell
tags must be valid Python identifiers after the `@` symbol. Cells can have any
number of tags.

```python 
"""
Put the solution to question 1 in this cell...
@answer1
"""

1 + 1
```

When a cell is executed the docstring is analyzed by the extension and the
cell's contents and result are stored in the tag cache. Other cells in the
notebook can access the cache: 

```python 
import nbtest

answer1 = nbtest.get('@answer1')
print("Answer source:", answer1.source)
print("Answer result value:", answer1.result.result)
```

## Unit Tests 

This extension registers the `%%testing` cell magic. Code in a `%%testing` cell
is expected to be Python. Code in a `%%testing` cell is run in its own package,
like unit tests would be. Arguments to `%%testing` are Python attributes in the
`__main__` namespace that will be imported into the testing namespace.  

```python
%%testing @answer1

assert answer1.run() == 2, "Error: 1 + 1 != 2"
```

Tests can be written as functions that begin with `test`:

```python
%%testing @answer1

def test_1p1(): 
    """Testing one plus one."""
    assert answer1.run() == 2, "Error: 1 + 1 != 2"
```

Function instances will be wrapped in a `unittest.FunctionTestCase`. You can
also write `TestCase`s directly:

```python
%%testing @answer1 

import unittest

class TestAdd(unittest.TestCase):
    def test_1p1(self): 
        """Testing one plus one."""
        selfAssertEqual(answer1.run(), 2, "Error: 1 + 1 != 2")
```

All of the features of `unittest` are supported so you can make arbitrarily
complex test cases. If you prefer to keep complex test code out of the notebook
and in a separate library you can use the `unittest`'s built in
[TestLoader](https://docs.python.org/3/library/unittest.html#loading-and-running-tests)
by passing strings (and other things) in the `nbtest_cases` variable:

```python
%%testing @answer1 

nbtest_cases = (
    "test_lib",
    "test_lib.ATestCase",
    "test_lib.lib_function"
)
```

### A Note on Namespaces
 
It's important to remember that notebook code exists in the `__main__` namespace
and `%%testing` code exists in a separate namespace. The `%%testing` namespace
is shared by all `%%testing` cells in the notebook. The most notable consequence
of the separation of namespaces is that `import`s done in normal cells are not
shared by `%%testing` cells and vice-versa. This means you might have to `import
math` two times in a notebook where you use `math.pi`. 
