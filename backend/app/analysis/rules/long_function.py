"""LONG_FUNCTION: слишком длинная функция."""

import ast

from ._common import finding, functions

MAX_LINES = 30


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти функции длиннее MAX_LINES строк."""
    result = []
    for func in functions(tree):
        length = (func.end_lineno or func.lineno) - func.lineno + 1
        if length > MAX_LINES:
            result.append(
                finding(
                    "LONG_FUNCTION",
                    "low",
                    func.lineno,
                    f"Функция {func.name} занимает {length} строк (больше {MAX_LINES}): "
                    "разбейте её на части.",
                )
            )
    return sorted(result, key=lambda item: item["line"])
