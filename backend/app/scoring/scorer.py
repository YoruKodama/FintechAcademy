"""Оценщик баллов: score(findings, llm_answer, text_answers) -> Result.

Часть баллов задают правила (замечания анализатора, длина ответов), часть берётся у модели.
Правила ограничивают балл сверху, модель может его только снизить. Функция чистая:
одинаковый ввод всегда даёт одинаковый итог.
"""

from collections.abc import Sequence

from app.llm.base import LLMResponseError
from app.llm.parsing import LLMAnswer, parse_llm_answer
from app.llm.types import (
    CRITERIA,
    MAX_CRITERION_SCORE,
    MAX_FEEDBACK_LEN,
    MAX_TOTAL_SCORE,
    Finding,
    Result,
)

from .rules import apply_finding_rules, explanation_cap, is_empty_solution

TEMPERATURE = 0.0

NO_MODEL_SCORE = 12

CRITERIA_NAMES = {
    "correctness": "правильность",
    "code_quality": "качество кода",
    "safety": "безопасность",
    "explanation": "ясность объяснения",
}

EMPTY_FEEDBACK = (
    "Решение пустое: код не найден, поэтому баллы не начислены. "
    "Напишите решение и отправьте снова."
)
NO_MODEL_FEEDBACK = (
    "Подробный разбор от модели получить не удалось, поэтому баллы за правильность и "
    "объяснение ориентировочные. Баллы за безопасность и качество кода посчитаны по правилам."
)


def _resolve_answer(llm_answer: LLMAnswer | str | None) -> LLMAnswer | None:
    if llm_answer is None or isinstance(llm_answer, LLMAnswer):
        return llm_answer
    try:
        return parse_llm_answer(llm_answer)
    except LLMResponseError:
        return None


def _rules_note(applied: list[tuple[str, str, int]]) -> str:
    if not applied:
        return ""
    parts = [
        f"{CRITERIA_NAMES[criterion]} −{penalty} ({code})"
        for code, criterion, penalty in applied
    ]
    return "Снято автоматическими правилами: " + ", ".join(parts) + "."


def _join_feedback(text: str, note: str) -> str:
    """Склеить разбор и пометку о правилах так, чтобы влезть в лимит; пометка важнее."""
    if not note:
        return text[:MAX_FEEDBACK_LEN]
    room = MAX_FEEDBACK_LEN - len(note) - 2
    if room <= 0:
        return note[:MAX_FEEDBACK_LEN]
    if len(text) > room:
        text = text[: room - 1].rstrip() + "…"
    return f"{text}\n\n{note}"


def score(
    findings: Sequence[Finding],
    llm_answer: LLMAnswer | str | None,
    text_answers: Sequence[str],
) -> Result:
    """Посчитать итоговый результат.

    `llm_answer` — разобранный ответ модели, сырая строка с ответом (она будет разобрана здесь)
    или None, если модель недоступна. Сломанный ответ не приводит к ошибке:
    баллы считаются по запасному правилу, а в разборе об этом сказано.
    """
    findings = list(findings)
    if is_empty_solution(findings):
        return Result(
            total=0,
            criteria=dict.fromkeys(CRITERIA, 0),
            feedback=EMPTY_FEEDBACK,
            findings=findings,
        )

    outcome = apply_finding_rules(findings)
    caps = dict(outcome.caps)
    caps["explanation"] = min(caps["explanation"], explanation_cap(text_answers))

    answer = _resolve_answer(llm_answer)
    criteria: dict[str, int] = {}
    for key in CRITERIA:
        if answer is not None:
            base = answer.criteria.get(key, 0)
        elif key in ("correctness", "explanation"):
            base = NO_MODEL_SCORE
        else:
            base = MAX_CRITERION_SCORE
        criteria[key] = max(0, min(int(base), caps[key], MAX_CRITERION_SCORE))

    feedback = _join_feedback(
        answer.feedback if answer is not None else NO_MODEL_FEEDBACK,
        _rules_note(outcome.applied),
    )
    total = max(0, min(sum(criteria.values()), MAX_TOTAL_SCORE))
    return Result(total=total, criteria=criteria, feedback=feedback, findings=findings)
