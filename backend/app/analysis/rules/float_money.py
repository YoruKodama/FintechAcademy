"""FLOAT_MONEY: вещественные числа в расчётах, где должны быть Decimal или целые копейки."""

import ast

from ._common import finding


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти дробные литералы и вызовы float()."""
    found: dict[int, dict] = {}
    for node in ast.walk(tree):
        is_literal = isinstance(node, ast.Constant) and isinstance(node.value, float)
        is_call = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "float"
        )
        if (is_literal or is_call) and node.lineno not in found:
            found[node.lineno] = finding(
                "FLOAT_MONEY",
                "high",
                node.lineno,
                "Используется float: для денег применяйте Decimal или целые копейки.",
            )
    return sorted(found.values(), key=lambda item: item["line"])
