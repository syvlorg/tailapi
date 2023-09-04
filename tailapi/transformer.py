# Adapted From:
# Answer: https://stackoverflow.com/a/18178379/10827766
# User: https://stackoverflow.com/users/918959/antti-haapala-%d0%a1%d0%bb%d0%b0%d0%b2%d0%b0-%d0%a3%d0%ba%d1%80%d0%b0%d1%97%d0%bd%d1%96

import ast


class Transformer(ast.NodeTransformer):
    ALLOWED_NAMES = set()
    ALLOWED_NODE_TYPES = set(("Expression", "BoolOp", "And", "Constant", "Or"))

    def generic_visit(self, node):
        nodetype = getattr(type(node), "__name__")
        if nodetype not in self.ALLOWED_NODE_TYPES:
            raise RuntimeError("Invalid expression: " + nodetype + " not allowed")
        return ast.NodeTransformer.generic_visit(self, node)
