"""
Transforms to manipulate code cells.
"""

import ast


class RewriteVariableAssignments(ast.NodeTransformer):
    """
    An AST transformer that rewrites package level variable assignments
    by changing the variable name to `_`.
    """

    def __init__(self, *names):
        self.targets = {*names}

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Store) and node.id in self.targets:
            node.id = "_"
        return node
