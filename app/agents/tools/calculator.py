"""Safe calculator tool for numeric computations."""

import ast
import math
import operator

from langchain_core.tools import tool

from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowed operators and functions for safe eval
_SAFE_OPERATORS: dict = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_SAFE_FUNCS: dict = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _SAFE_FUNCS:
        return _SAFE_FUNCS[node.id]  # type: ignore[return-value]
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](
            _safe_eval(node.left), _safe_eval(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        func = _safe_eval(node.func)
        if callable(func):
            args = [_safe_eval(a) for a in node.args]
            return float(func(*args))
    raise ValueError(f"Unsafe expression node: {type(node).__name__}")


@tool
def calculator(expression: str) -> dict:
    """Evaluate a mathematical expression safely.

    Supports: +, -, *, /, **, sqrt, log, log10, abs, round, min, max, floor, ceil, pi, e.

    Args:
        expression: A mathematical expression as a string, e.g. "sqrt(144) + 3 * pi".

    Returns:
        Dict with keys: expression, result (float), error (str or None).
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        logger.debug("calculator_ok", expression=expression, result=result)
        return {"expression": expression, "result": result, "error": None}
    except Exception as exc:
        logger.warning("calculator_failed", expression=expression, error=str(exc))
        return {"expression": expression, "result": None, "error": str(exc)}
