"""
Transforms to manipulate code cells.
"""

import ast


class RewriteVariableAssignments(ast.NodeTransformer):
    """
    An AST transformer that rewrites package level variable assignments
    by changing the variable name to `_`. The search excludes assignments 
    inside of functions, classes or compound statements such as "if", "for" 
    and "try"
    """

    def __init__(self, *names):
        self.targets = {*names}
        self.stack = []
        self.visit_FunctionDef = self._disable_visit
        self.visit_AsyncFunctionDef = self._disable_visit
        self.visit_ClassDef = self._disable_visit
        self.visit_For = self._disable_visit
        self.visit_AsyncFor = self._disable_visit
        self.visit_While = self._disable_visit
        self.visit_If = self._disable_visit
        self.visit_With = self._disable_visit
        self.visit_AsyncWith = self._disable_visit
        self.visit_Match = self._disable_visit
        self.visit_Try = self._disable_visit

        
    def visit_Name(self, node: ast.Name) -> ast.AST:
        if len(self.stack) == 0 and isinstance(node.ctx, ast.Store) and node.id in self.targets:
            node.id = "_"
        return node

    def _disable_visit(self, node):
        self.stack.append(node)
        super().generic_visit(node)
        self.stack.pop()
        return node
        
