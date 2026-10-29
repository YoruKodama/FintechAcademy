"""BARE_EXCEPT: except без типа и слишком широкий except Exception."""

import ast

from ._common import finding

_BROAD = {"Exception", "BaseException"}


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти пустой except и перехват слишком общих исключений."""
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            result.append(
                finding(
                    "BARE_EXCEPT",
                    "medium",
                    node.lineno,
                    "except без типа скрывает любые ошибки: укажите конкретное исключение.",
                )
            )
        elif isinstance(node.type, ast.Name) and node.type.id in _BROAD:
            result.append(
                finding(
                    "BARE_EXCEPT",
                    "low",
                    node.lineno,
                    f"Слишком широкий перехват {node.type.id}: перехватывайте нужные ошибки.",
                )
            )
    return sorted(result, key=lambda item: item["line"])
