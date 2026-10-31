"""Правила баллов: что снимают замечания анализатора и ответы на вопросы.

Правила детерминированы: одинаковые замечания всегда дают одинаковые ограничения.
Правило задаёт верхнюю границу балла по критерию; модель может поставить меньше,
но не больше.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.llm.types import CRITERIA, MAX_CRITERION_SCORE, Finding

EMPTY_SOLUTION = "EMPTY_SOLUTION"

RULES: dict[str, tuple[str, int]] = {
    "FLOAT_MONEY": ("safety", 10),
    "NO_VALIDATION": ("safety", 8),
    "HARDCODED_SECRET": ("safety", 12),
    "BARE_EXCEPT": ("code_quality", 4),
    "SYNTAX_ERROR": ("correctness", MAX_CRITERION_SCORE),
    # Коды анализатора (app.analysis): штраф снижает верхнюю границу критерия.
    "NO_INPUT_VALIDATION": ("safety", 8),
    "EVAL_EXEC": ("safety", MAX_CRITERION_SCORE),
    "TESTS_FAILED": ("correctness", 15),
    "TIMEOUT": ("correctness", 20),
    "MISSING_RETURN": ("correctness", 5),
    "UNUSED_VARIABLE": ("code_quality", 5),
    "LONG_FUNCTION": ("code_quality", 8),
    "DEEP_NESTING": ("code_quality", 10),
}

SEVERITY_PENALTY: dict[str, int] = {"low": 1, "medium": 3, "high": 6}
UNKNOWN_SEVERITY_PENALTY = SEVERITY_PENALTY["low"]

MIN_ANSWER_CHARS = 40
SHORT_ANSWERS_CAP = 10


@dataclass
class RuleOutcome:
    """Верхние границы баллов по критериям и список применённых правил."""

    caps: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(CRITERIA, MAX_CRITERION_SCORE)
    )
    applied: list[tuple[str, str, int]] = field(default_factory=list)


def is_empty_solution(findings: Sequence[Finding]) -> bool:
    """Анализатор сообщил, что решения нет (пустой файл или только комментарии)."""
    return any(finding.get("code") == EMPTY_SOLUTION for finding in findings)


def apply_finding_rules(findings: Sequence[Finding]) -> RuleOutcome:
    """Посчитать ограничения по баллам из замечаний анализатора."""
    outcome = RuleOutcome()
    seen: set[str] = set()
    for finding in findings:
        code = str(finding.get("code", ""))
        if not code or code == EMPTY_SOLUTION or code in seen:
            continue
        seen.add(code)
        if code in RULES:
            criterion, penalty = RULES[code]
        else:
            criterion = "code_quality"
            penalty = SEVERITY_PENALTY.get(str(finding.get("severity")), UNKNOWN_SEVERITY_PENALTY)
        outcome.caps[criterion] = max(0, outcome.caps[criterion] - penalty)
        outcome.applied.append((code, criterion, penalty))
    return outcome


def explanation_cap(text_answers: Sequence[str]) -> int:
    """Ограничение балла за объяснение по самим ответам: пустые и слишком короткие ответы."""
    answers = [answer.strip() for answer in text_answers if answer and answer.strip()]
    if not answers:
        return 0
    average = sum(len(answer) for answer in answers) / len(answers)
    return SHORT_ANSWERS_CAP if average < MIN_ANSWER_CHARS else MAX_CRITERION_SCORE
