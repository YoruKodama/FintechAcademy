"""Полный путь одного решения: обезличивание -> модель -> оценщик баллов.

Любой текст уходит в модель только отсюда и только после `anonymize`.
"""

import logging
import re
from collections.abc import Sequence

from app.llm.base import LLMClient, LLMError
from app.llm.parsing import LLMAnswer, complete_json
from app.llm.prompt_loader import load_prompt
from app.llm.types import Finding, Result
from app.privacy import anonymize

from .scorer import TEMPERATURE, score

logger = logging.getLogger(__name__)

MAX_TOKENS = 800
_SERVICE_TAGS = re.compile(r"</?(task|code|findings|answers)>", re.IGNORECASE)


def _neutralize(text: str) -> str:
    """Убрать из пользовательского текста служебные теги, чтобы он не ломал разметку промпта."""
    return _SERVICE_TAGS.sub(lambda match: match.group(0).replace("<", "‹").replace(">", "›"), text)


def build_user_message(
    code: str,
    findings: Sequence[Finding],
    questions: Sequence[str],
    answers: Sequence[str],
    task: str | None = None,
) -> str:
    """Собрать сообщение для модели по формату из prompts/review_code.md."""
    parts = []
    if task:
        parts.append(f"<task>\n{_neutralize(task)}\n</task>")
    parts.append(f"<code>\n{_neutralize(code)}\n</code>")

    if findings:
        lines = [
            f"- [{item['severity']}] строка {item['line']}, {item['code']}: {item['message']}"
            for item in findings
        ]
    else:
        lines = ["- замечаний нет"]
    parts.append("<findings>\n" + "\n".join(lines) + "\n</findings>")

    qa = []
    for index, answer in enumerate(answers, start=1):
        question = questions[index - 1] if index <= len(questions) else "(вопрос не указан)"
        qa.append(f"Вопрос {index}: {question}\nОтвет {index}: {answer or '(нет ответа)'}")
    parts.append("<answers>\n" + ("\n\n".join(qa) if qa else "(ответов нет)") + "\n</answers>")
    return "\n\n".join(parts)


def evaluate_solution(
    client: LLMClient,
    code: str,
    findings: Sequence[Finding],
    questions: Sequence[str],
    text_answers: Sequence[str],
    task: str | None = None,
) -> Result:
    """Проверить решение. Недоступная модель не ломает проверку: баллы считаются по правилам."""
    user_message = build_user_message(code, findings, questions, text_answers, task)
    safe_message, _mapping = anonymize(user_message)
    answer: LLMAnswer | None
    try:
        answer = complete_json(
            client,
            load_prompt("review_code"),
            safe_message,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
    except LLMError as error:
        logger.warning("Модель не дала разбор: %s", error)
        answer = None
    return score(findings, answer, text_answers)
