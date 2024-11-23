"""
Helpers that analyze code cells.
"""

import ast
import copy
import types
import typing


class AnalysisNode:
    """
    An API for simple syntax analysis.
    """

    def __init__(self, source, tree=None):
        """
        Create an analysis node with optional source code.

        source: Source code.
        tree: The parse tree or subtree corresponding to the source. If tree is
            None it will be generated using ast.parse(source)
        """

        self._source = source
        self._tree = tree
        if tree is None and source is not None:
            self._tree = ast.parse(source)

    @property
    def source(self) -> str:
        """
        The source corresponding to the tokens in tree. If this node is a
        subtree only the source corresponding to the subtree is returned.
        """
        src = ast.get_source_segment(self._source, self._tree)
        if src is None:
            return self._source
        else:
            return src

    @property
    def tree(self) -> ast.Module:
        """
        A deep copy of the parse tree or subtree that corresponding to this
        node.
        """
        if self._tree.__class__ == MarkerNode:
            # Don't show users my fake node.
            return copy.deepcopy(self._tree._real_node)
        else:
            return copy.deepcopy(self._tree)

    @property
    def docstring(self) -> typing.Union[str, None]:
        """The docstring of this node. `None` if there is no docstring."""
        if self._tree.__class__ == MarkerNode:
            return ast.get_docstring(self._tree._real_node)
        return ast.get_docstring(self._tree)

    @property
    def tokens(self) -> set:
        """A set of token classes from the current scope."""

        class RootExtractor(ast.NodeTransformer):
            def __init__(self):
                self.depth = 0

            def delete_body(self, node: ast.AST):
                if self.depth == 0:
                    self.depth += 1
                    self.generic_visit(node)
                    self.depth -= 1
                else:
                    node.body = []
                return node

            def visit_Module(self, node):
                self.depth += 1
                self.generic_visit(node)
                self.depth = -1
                return node

            def visit_ClassDef(self, node: ast.ClassDef):
                return self.delete_body(node)

            def visit_FunctionDef(self, node: ast.FunctionDef):
                return self.delete_body(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                return self.delete_body(node)

        return set(
            (x.__class__ for x in ast.walk(RootExtractor().visit(self.tree)))
        )

    @property
    def functions(self) -> dict[str, types.FunctionType]:
        """
        A dictionary of the names of defined functions and their corresponding
        AnalysisNode.
        """
        found = {}

        class FindFunctions(RootNodeFinder):
            """
            A visitor that finds function definitions at the top level of the
            tree.
            """

            def visit_FunctionDef(_, node: ast.FunctionDef):
                found[node.name] = AnalysisNode(self._source, MarkerNode(node))

            def visit_AsyncFunctionDef(_, node: ast.FunctionDef):
                found[node.name] = AnalysisNode(self._source, MarkerNode(node))

        finder = FindFunctions()
        finder.visit(self._tree)
        return found

    @property
    def classes(self) -> dict[str, type]:
        """
        A dictionary of the names of defined classes and their corresponding
        AnalysisNode.
        """
        found = {}

        class FindClasses(RootNodeFinder):
            """
            A visitor that finds class definitions at the top level of the tree.
            """

            def visit_ClassDef(_, node: ast.ClassDef):
                found[node.name] = AnalysisNode(self._source, MarkerNode(node))

        finder = FindClasses()
        finder.visit(self._tree)
        return found

    def _assignments(self) -> list[str]:
        found = []

        class FindAssignments(RootNodeFinder):
            def visit_Name(self, node: ast.Name):
                if isinstance(node.ctx, ast.Store):
                    found.append(node.id)
                self.generic_visit(node)

        finder = FindAssignments()
        finder.visit(self._tree)
        return found

    @property
    def assignments(self) -> set[str]:
        """
        The set of the names of assigned variables in this node.
        """
        return set(self._assignments())

    def count_assignments(self, name) -> set[str]:
        """
        Count the number of times the variable `name` is assigned.
        """
        return self._assignments().count(name)

    def _references(self) -> list[str]:
        found = []

        class FindAllNames(RootNodeFinder):
            def visit_Name(self, node: ast.Name):
                if isinstance(node.ctx, ast.Load):
                    found.append(node.id)
                self.generic_visit(node)

        finder = FindAllNames()
        finder.visit(self._tree)
        return found

    @property
    def references(self) -> set[str]:
        """
        The set of the names of referenced attributes in this node. References
        are context loads, not stores. Assignments do not count as references.
        """
        return set(self._references())

    def count_references(self, name) -> set[str]:
        """
        Count the number of times the symbol `name` is referenced.
        """
        return self._references().count(name)

    @property
    def constants(self) -> set[typing.Any]:
        """
        The set of all literal values in this node.
        """
        found = []

        class FindConstants(RootNodeFinder):
            def visit_Constant(self, node: ast.Constant):
                found.append(node.value)
                self.generic_visit(node)

        finder = FindConstants()
        finder.visit(self._tree)
        return set(found)

    def _calls(self) -> list[str]:
        """
        The set of names of the functions called in this node.
        """
        found = []

        class FindCalls(RootNodeFinder):
            def visit_Call(self, node: ast.Call):
                found.append(
                    node.func.id
                    if hasattr(node.func, "id")
                    else node.func.attr
                )
                self.generic_visit(node)

        finder = FindCalls()
        finder.visit(self._tree)
        return found

    @property
    def calls(self) -> set[str]:
        """
        The set of names of the functions called in this node.
        """
        return set(self._calls())

    def count_calls(self, name) -> set[str]:
        """
        Count the number of times the function `name` is called.
        """
        return self._calls().count(name)

    @property
    def arguments(self) -> set[str]:
        """
        If the current node is a function definition, the list of argument
        names in definition order.
        """
        found = []

        t = self.tree
        if t.__class__ not in (ast.FunctionDef, ast.AsyncFunctionDef):
            raise ValueError("Cannot call arguments on a non-function.")

        for arg in t.args.posonlyargs + t.args.args:
            found.append(arg.arg)

        if t.args.vararg is not None:
            found.append(f"*{t.args.vararg.arg}")

        for arg in t.args.kwonlyargs:
            found.append(arg.arg)

        if t.args.kwarg is not None:
            found.append(f"**{t.args.kwarg.arg}")

        return found

    @property
    def imports(self) -> set[str]:
        """
        The set of modules imported in this node. Entries have the true module
        name, not the alias given with an "as", or a single attribute was imported
        with "from." For example, all of these are equivalent an report "foo" as
        the import:

        import foo
        import foo as bar
        from foo import bak
        """
        found = []

        class FindImports(RootNodeFinder):
            def visit_Import(self, node: ast.Call):
                nonlocal found
                found += [alias.name for alias in node.names]

            def visit_ImportFrom(self, node: ast.Call):
                found.append(node.module)

        finder = FindImports()
        finder.visit(self._tree)
        return set(found)


class MarkerNode(ast.AST):
    """
    A fake Module node to use as the root of a tree that is rooted on a
    ast.Class or ast.Function node. Using this as the root makes the visitors
    that refuse to descend into function or class definitions just work.
    """

    def __init__(self, root: ast.AST):
        """
        Initialize a marker node from a new root.
        """
        self._real_node = root

        # Preserve source information
        self.lineno = root.lineno
        self.end_lineno = root.end_lineno
        self.col_offset = root.col_offset
        self.end_col_offset = root.end_col_offset

        self._fields = ["body"]
        self.body = root.body


class RootNodeFinder(ast.NodeVisitor):
    """
    A visitor that does not descend into class or function definitions.
    """

    def visit_ClassDef(self, node: ast.ClassDef):
        pass

    def visit_FunctionDef(self, node: ast.FunctionDef):
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        pass
