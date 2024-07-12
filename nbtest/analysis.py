"""
Helpers that analyze code cells.
"""

import ast


class TopLevelDefines(ast.NodeVisitor):
    """
    A NodeVisitor that finds all functions, classes and variables that have
    been defined at the package level.
    """

    def __init__(self):
        self.defs = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defs.append(
            (
                node.name,
                ast.FunctionDef,
            )
        )

    def visit_AsyncFunctionDef(
        self,
        node: ast.FunctionDef,
    ):
        self.defs.append(
            (
                node.name,
                ast.FunctionDef,
            )
        )

    def visit_ClassDef(self, node: ast.FunctionDef):
        self.defs.append(
            (
                node.name,
                ast.ClassDef,
            )
        )

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.defs.append(
                (
                    node.id,
                    ast.Assign,
                )
            )
