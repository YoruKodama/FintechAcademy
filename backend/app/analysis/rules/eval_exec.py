"""EVAL_EXEC: вызовы eval и exec выполняют произвольный код."""

import ast

from ._common import finding

_DANGEROUS = {"eval", "exec"}


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти вызовы eval() и exec()."""
    return sorted(
        (
            finding(
                "EVAL_EXEC",
                "high",
                node.lineno,
                f"Вызов {node.func.id}() выполняет произвольный код: уберите его.",
            )
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _DANGEROUS
        ),
        key=lambda item: item["line"],
    )
