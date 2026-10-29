"""NO_INPUT_VALIDATION: функция принимает данные и нигде их не проверяет."""

import ast

from ._common import finding, functions

_CHECKS = (ast.Raise, ast.Assert, ast.Try)


def _params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = func.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    return [name for name in names if name not in {"self", "cls"}]


def _validates(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(func):
        if isinstance(node, _CHECKS):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"isinstance", "issubclass"}
        ):
            return True
    return False


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти функции с параметрами, где нет ни raise, ни assert, ни try, ни isinstance."""
    result = []
    for func in functions(tree):
        if func.name.startswith("__") or not _params(func):
            continue
        if not _validates(func):
            result.append(
                finding(
                    "NO_INPUT_VALIDATION",
                    "medium",
                    func.lineno,
                    f"Функция {func.name} не проверяет входные данные: "
                    "добавьте проверки и понятные ошибки.",
                )
            )
    return sorted(result, key=lambda item: item["line"])
