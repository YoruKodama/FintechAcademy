"""Общие типы данных LLM-слоя и оценщика баллов."""

from typing import TypedDict

CRITERIA: tuple[str, ...] = ("correctness", "code_quality", "safety", "explanation")
MAX_CRITERION_SCORE = 25
MAX_TOTAL_SCORE = MAX_CRITERION_SCORE * len(CRITERIA)
MAX_FEEDBACK_LEN = 1200


class Finding(TypedDict):
    """Замечание статического анализа к решению."""

    code: str
    severity: str
    line: int
    message: str


class Result(TypedDict):
    """Итог проверки решения."""

    total: int
    criteria: dict[str, int]
    feedback: str
    findings: list[Finding]
