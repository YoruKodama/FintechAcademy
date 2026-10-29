"""MISSING_RETURN: функция возвращает значение не на всех путях выполнения."""

import ast

from ._common import finding, functions


def _terminates(body: list[ast.stmt]) -> bool:
    """Верно, если выполнение блока всегда заканчивается return или raise."""
    for stmt in body:
        if isinstance(stmt, ast.Return | ast.Raise):
            return True
        if isinstance(stmt, ast.If) and stmt.orelse:
            if _terminates(stmt.body) and _terminates(stmt.orelse):
                return True
        elif isinstance(stmt, ast.Try):
            handlers = all(_terminates(handler.body) for handler in stmt.handlers)
            main = _terminates(stmt.body) or (stmt.orelse and _terminates(stmt.orelse))
            if (main and handlers) or (stmt.finalbody and _terminates(stmt.finalbody)):
                return True
        elif isinstance(stmt, ast.With | ast.AsyncWith):
            if _terminates(stmt.body):
                return True
        elif isinstance(stmt, ast.While):
            infinite = isinstance(stmt.test, ast.Constant) and stmt.test.value is True
            has_break = any(isinstance(node, ast.Break) for node in ast.walk(stmt))
            if infinite and not has_break:
                return True
    return False


def _returns_value(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(isinstance(node, ast.Return) and node.value is not None for node in ast.walk(func))


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти функции, где значение возвращается не во всех ветках."""
    result = []
    for func in functions(tree):
        if _returns_value(func) and not _terminates(func.body):
            result.append(
                finding(
                    "MISSING_RETURN",
                    "medium",
                    func.end_lineno or func.lineno,
                    f"В функции {func.name} есть ветка без return: "
                    "верните значение или вызовите исключение на всех путях.",
                )
            )
    return sorted(result, key=lambda item: item["line"])
