"""DEEP_NESTING: вложенность блоков глубже трёх уровней."""

import ast

from ._common import finding, functions

MAX_DEPTH = 3
_BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)


def _deepest(node: ast.AST, depth: int) -> tuple[int, int]:
    """Вернуть (максимальная глубина, строка самого глубокого блока) внутри node."""
    best = (depth, getattr(node, "lineno", 1))
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        child_depth = depth + 1 if isinstance(child, _BLOCKS) else depth
        candidate = _deepest(child, child_depth)
        if isinstance(child, _BLOCKS) and child_depth > candidate[0]:
            candidate = (child_depth, child.lineno)
        if candidate[0] > best[0]:
            best = candidate
    return best


def check(tree: ast.AST, source: str) -> list[dict]:
    """Найти функции, где блоки if/for/while/try/with вложены глубже MAX_DEPTH."""
    result = []
    for func in functions(tree):
        depth, line = _deepest(func, 0)
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
