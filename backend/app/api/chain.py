"""Цепочка проверки решения на submit: анализ кода, обезличивание, модель, оценщик.

Модули Юры (анализ кода) и Ангелины (цепочка модели и оценщик) подключаются автоматически,
когда появляются; до этого работают заглушки, чтобы API проходил сценарий целиком.
"""

import logging
import os

from app.llm import LLMError, get_llm_client
from app.privacy import anonymize

log = logging.getLogger(__name__)

STUB_NOTE = "Оценщик ещё не подключён: показан предварительный результат-заглушка."
SYSTEM_PROMPT = "Ты ревьюер кода. Отвечай по-русски."


def analyze_code(code: str, tests: str | None = None) -> list[dict]:
    """Найти замечания в коде и, если запуск включён, добавить итог прогона на тестах задачи.

    Запуск в контейнере включается переменной SANDBOX_ENABLED=1. Упавшие тесты и превышение
    лимита времени превращаются в замечания TESTS_FAILED и TIMEOUT.
    """
    from app.analysis import analyze, run_tests

    findings = list(analyze(code))
    if tests and os.getenv("SANDBOX_ENABLED") == "1":
        try:
            run = run_tests(code, tests)
        except ValueError as exc:
            log.error("Проверки сценария заданы неверно, запуск пропущен: %s", exc)
            return findings
        if run["status"] == "failed":
            findings.append(
                {
                    "code": "TESTS_FAILED",
                    "severity": "high",
                    "line": 1,
                    "message": f"Решение не прошло проверки задачи. {run['output']}"[:300],
                }
            )
        elif run["status"] == "timeout":
            findings.append(
                {
                    "code": "TIMEOUT",
                    "severity": "high",
                    "line": 1,
                    "message": "Решение превысило лимит времени выполнения.",
                }
            )
    return findings


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


def run_chain(
    code: str,
    answers: list[str],
    tests: str | None = None,
    questions: list[str] | None = None,
    task: str | None = None,
) -> dict:
    """Выполнить цепочку проверки и вернуть Result в виде словаря.

    Анализ кода и запуск на тестах, затем оценщик Ангелины: он сам обезличивает текст,
    вызывает модель и считает баллы. Если оценщик не импортируется, работает заглушка.
    """
    findings = analyze_code(code, tests)
    try:
        from app.scoring.pipeline import evaluate_solution
    except ImportError:
        return _stub_pipeline(code, answers, findings)
    result = evaluate_solution(
        get_llm_client(), code, findings, questions or [], answers, task=task
    )
    return dict(result)
