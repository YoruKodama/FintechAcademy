"""Общие помощники правил анализатора."""

import ast
from collections.abc import Iterator

FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def finding(code: str, severity: str, line: int, message: str) -> dict:
    """Собрать замечание в формате Finding из контракта."""
    return {"code": code, "severity": severity, "line": max(1, line), "message": message}


def functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Все функции и методы модуля, включая вложенные."""
    for node in ast.walk(tree):
        if isinstance(node, FUNCTION_NODES):
            yield node
