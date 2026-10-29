"""Анализ кода кандидата: замечания по правилам и безопасный запуск на тестах задачи."""

import ast

from .rules import ALL_RULES
from .rules._common import finding
from .sandbox import RunResult, run_tests

MAX_CODE_CHARS = 20_000

__all__ = ["RunResult", "analyze", "run_tests"]


def analyze(code: str) -> list[dict]:
    """Найти замечания в коде. Код не выполняется, разбор только через ast.

    Возвращает список Finding, отсортированный по номеру строки. Синтаксическая ошибка
    и слишком длинный код тоже превращаются в замечания, а не в исключение.
    """
    if len(code) > MAX_CODE_CHARS:
        return [
            finding(
                "CODE_TOO_LONG",
                "medium",
                1,
                f"Код длиннее {MAX_CODE_CHARS} символов: анализ пропущен.",
            )
        ]
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None) or 1
        return [finding("SYNTAX_ERROR", "high", line, "Синтаксическая ошибка: код не разбирается.")]

    findings = [item for rule in ALL_RULES for item in rule.check(tree, code)]
    return sorted(findings, key=lambda item: (item["line"], item["code"]))
