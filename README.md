# Notebook Embedded Unit Tests 

This is an IPython extension that makes it possible to write expressive and safe unit tests for notebooks. The extension makes it possible to identify notebook cells by a tag in a docstring. Test code can analyze and run cells and manipulate notebook variables and values. 

## Tagging Cells 

I major missing feature of Juptyer is the ability to introspect a notebook. While it's possible to find a cell by tag in the Javascript frontend, there is not currently a way to do that in the Python back end. This notebook extension watches cell executions and scans for tags in a cell's docstring. 

```python 
"""
@mycelltag
"""

print("Hello World")
```

