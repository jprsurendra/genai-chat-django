import ast
import operator
import logging

logger = logging.getLogger(__name__)

# Safe operators for the calculator
# Safe operators for the calculator
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,  # 🔥 NEW: Handles ** (Power)
    ast.USub: operator.neg,
}


def calculate(expression: str) -> str:
    """
    Safely evaluates a mathematical expression.
    """
    try:
        # 🔥 FIX: Convert '^' (common math syntax) to '**' (Python syntax for power)
        expression = expression.replace('^', '**')

        # Parse the expression into a syntax tree (safe from code injection)
        node = ast.parse(expression, mode='eval').body

        def _eval(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                return OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                return OPERATORS[type(node.op)](_eval(node.operand))
            else:
                raise TypeError(f"Unsupported operation: {type(node)}")

        result = _eval(node)
        return str(result)
    except Exception as e:
        logger.error(f"Calculator error for '{expression}': {e}")
        return f"Error: Could not calculate '{expression}'"