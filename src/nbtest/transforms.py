"""
Transforms to manipulate code cells.
"""

import ast


class RewriteVariableAssignments(ast.NodeTransformer):
    """
    An AST transformer that rewrites package level variable assignments
    by changing the variable name to `_`. The search excludes assignments
    inside of functions, classes or compound statements such as "if", "for"
    and "try" by limiting changes to tokens that are three deep from the
    root module.
    """

    def __init__(self, *names):
        self.targets = {*names}
        self.depth = 0
        self.rewrite = False

    def generic_visit(self, node: ast.AST) -> ast.AST:
        self.depth += 1
        n = super().generic_visit(node)
        self.depth -= 1
        return n

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        if self.depth == 1:
            self.rewrite = True
            n = self.generic_visit(node)
            self.rewrite = False
            return n
        else:
            return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if (
            self.rewrite
            and isinstance(node.ctx, ast.Store)
            and node.id in self.targets
        ):
            node.id = "_"
        return node
