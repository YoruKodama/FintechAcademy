"""UNUSED_VARIABLE: локальная переменная присвоена, но нигде не используется."""

import ast

from ._common import finding, functions


def _assigned(func: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, int]:
    """Имена, которым присваивается значение в функции, и строка первого присваивания."""
    names: dict[str, int] = {}
    for node in ast.walk(func):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.setdefault(target.id, target.lineno)
    return names


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти переменные, значение которых не читается."""
    result = []
    for func in functions(tree):
        declared: set[str] = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Global | ast.Nonlocal):
                declared.update(node.names)
        used = {
            node.id
            for node in ast.walk(func)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        for name, line in _assigned(func).items():
            if name.startswith("_") or name in used or name in declared:
                continue
            result.append(
                finding(
                    "UNUSED_VARIABLE",
                    "low",
                    line,
                    f"Переменная {name} присвоена, но не используется: удалите её.",
                )
            )
    return sorted(result, key=lambda item: item["line"])
