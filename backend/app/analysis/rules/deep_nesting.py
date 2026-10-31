"""DEEP_NESTING: вложенность блоков глубже трёх уровней."""

import ast

from ._common import finding, functions

MAX_DEPTH = 3
_BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)


def _elif_nodes(func: ast.AST) -> set[int]:
    """Узлы If, которые на самом деле elif: единственное содержимое else у родительского If."""
    return {
        id(node.orelse[0])
        for node in ast.walk(func)
        if isinstance(node, ast.If) and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)
    }


def _deepest(node: ast.AST, depth: int, elifs: set[int]) -> tuple[int, int]:
    """Вернуть (максимальная глубина, строка самого глубокого блока) внутри node."""
    best = (depth, getattr(node, "lineno", 1))
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        is_block = isinstance(child, _BLOCKS) and id(child) not in elifs
        child_depth = depth + 1 if is_block else depth
        candidate = _deepest(child, child_depth, elifs)
        if is_block and child_depth > candidate[0]:
            candidate = (child_depth, child.lineno)
        if candidate[0] > best[0]:
            best = candidate
    return best


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти функции, где блоки if/for/while/try/with вложены глубже MAX_DEPTH."""
    result = []
    for func in functions(tree):
        depth, line = _deepest(func, 0, _elif_nodes(func))
        if depth > MAX_DEPTH:
            result.append(
                finding(
                    "DEEP_NESTING",
                    "medium",
                    line,
                    f"Вложенность {depth} уровня в {func.name} (допустимо {MAX_DEPTH}): "
                    "вынесите вложенную логику или используйте ранний выход.",
                )
            )
    return sorted(result, key=lambda item: item["line"])
