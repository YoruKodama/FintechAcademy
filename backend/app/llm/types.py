"""Общие типы данных LLM-слоя и оценщика баллов."""

from typing import TypedDict

# Четыре критерия оценки, по 25 баллов каждый.
CRITERIA: tuple[str, ...] = ("correctness", "code_quality", "safety", "explanation")
MAX_CRITERION_SCORE = 25
MAX_TOTAL_SCORE = MAX_CRITERION_SCORE * len(CRITERIA)
MAX_FEEDBACK_LEN = 1200


class Finding(TypedDict):
    """Замечание статического анализа к решению."""

    code: str  # машинный код замечания, например "FLOAT_MONEY"
    severity: str  # "low" | "medium" | "high"
    line: int  # номер строки в решении
    message: str  # текст замечания по-русски


class Result(TypedDict):
    """Итог проверки решения."""

    total: int  # 0..100
    criteria: dict[str, int]  # correctness, code_quality, safety, explanation: 0..25
    feedback: str  # разбор по-русски, до 1200 символов
    findings: list[Finding]
