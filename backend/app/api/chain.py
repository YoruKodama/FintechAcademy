"""Цепочка проверки решения на submit: анализ кода, обезличивание, модель, оценщик.

Модули Юры (анализ кода) и Ангелины (цепочка модели и оценщик) подключаются автоматически,
когда появляются; до этого работают заглушки, чтобы API проходил сценарий целиком.
"""

import logging

from app.llm import LLMError, get_llm_client
from app.privacy import anonymize

log = logging.getLogger(__name__)

STUB_NOTE = "Оценщик ещё не подключён: показан предварительный результат-заглушка."
SYSTEM_PROMPT = "Ты ревьюер кода. Отвечай по-русски."


def analyze_code(code: str) -> list[dict]:
    """Найти замечания в коде. Пока анализатора нет, возвращает пустой список."""
    try:
        from app.analysis import analyze
    except ImportError:
        return []
    return list(analyze(code))


def _stub_pipeline(code: str, answers: list[str], findings: list[dict]) -> dict:
    """Заглушка цепочки: обезличивание и вызов модели без настоящего оценщика."""
    safe_code, _ = anonymize(code)
    safe_answers = [anonymize(answer)[0] for answer in answers]
    prompt = f"Код:\n{safe_code}\n\nОтветы:\n" + "\n".join(safe_answers)
    try:
        comment = get_llm_client().complete(SYSTEM_PROMPT, prompt)
    except LLMError as exc:
        log.warning("Модель недоступна: %s", exc)
        comment = "Модель сейчас недоступна, разбор не сформирован."
    each = max(0, 15 - 5 * len(findings))
    criteria = {
        "correctness": each,
        "code_quality": each,
        "safety": each,
        "explanation": each,
    }
    return {
        "total": sum(criteria.values()),
        "criteria": criteria,
        "feedback": f"{STUB_NOTE} {comment}"[:1200],
        "findings": findings,
    }


def run_chain(code: str, answers: list[str]) -> dict:
    """Выполнить цепочку проверки и вернуть Result в виде словаря."""
    findings = analyze_code(code)
    try:
        from app.pipeline import run_pipeline
    except ImportError:
        return _stub_pipeline(code, answers, findings)
    return dict(run_pipeline(code, answers, findings))
