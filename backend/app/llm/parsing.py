"""Разбор ответа модели: строгий JSON {"criteria": {...}, "feedback": "..."}."""

import json
import re
from dataclasses import dataclass

from .base import LLMClient, LLMResponseError
from .types import CRITERIA, MAX_CRITERION_SCORE, MAX_FEEDBACK_LEN

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

RETRY_HINT = (
    "Предыдущий ответ не соответствует формату: {reason}. "
    "Верни только один JSON-объект вида "
    '{{"criteria": {{"correctness": 0, "code_quality": 0, "safety": 0, "explanation": 0}}, '
    '"feedback": "текст по-русски"}} без пояснений и без markdown.'
)


@dataclass(frozen=True)
class LLMAnswer:
    """Проверенный ответ модели."""

    criteria: dict[str, int]
    feedback: str


def _extract_json(raw: str) -> str:
    """Достать JSON из ответа: модель может обернуть его в ```json ... ``` или добавить текст."""
    fenced = _FENCE.search(raw)
    candidate = fenced.group(1) if fenced else raw
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end <= start:
        raise LLMResponseError("в ответе нет JSON-объекта")
    return candidate[start : end + 1]


def _to_score(key: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise LLMResponseError(f"балл за {key} должен быть числом")
    try:
        number = float(value)
    except ValueError:
        raise LLMResponseError(f"балл за {key} должен быть числом") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise LLMResponseError(f"балл за {key} должен быть конечным числом")
    return max(0, min(MAX_CRITERION_SCORE, round(number)))


def parse_llm_answer(raw: str) -> LLMAnswer:
    """Проверить формат ответа модели.

    Бросает LLMResponseError, если JSON сломан или нет нужных полей.
    Баллы за пределами 0..25 обрезаются до границ, слишком длинный разбор сокращается.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise LLMResponseError("модель вернула пустой ответ")
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        raise LLMResponseError("ответ не является корректным JSON") from None
    if not isinstance(data, dict):
        raise LLMResponseError("JSON должен быть объектом")

    criteria = data.get("criteria")
    if not isinstance(criteria, dict):
        raise LLMResponseError("нет объекта criteria")
    missing = [key for key in CRITERIA if key not in criteria]
    if missing:
        raise LLMResponseError("в criteria нет полей: " + ", ".join(missing))

    feedback = data.get("feedback")
    if not isinstance(feedback, str) or not feedback.strip():
        raise LLMResponseError("нет текста feedback")

    return LLMAnswer(
        criteria={key: _to_score(key, criteria[key]) for key in CRITERIA},
        feedback=feedback.strip()[:MAX_FEEDBACK_LEN],
    )


def complete_json(
    client: LLMClient,
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> LLMAnswer:
    """Вызвать модель и разобрать ответ. При сломанном JSON делается один повторный запрос."""
    raw = client.complete(system, user, temperature=temperature, max_tokens=max_tokens)
    try:
        return parse_llm_answer(raw)
    except LLMResponseError as first_error:
        retry_user = f"{user}\n\n{RETRY_HINT.format(reason=first_error)}"
        raw = client.complete(system, retry_user, temperature=temperature, max_tokens=max_tokens)
        try:
            return parse_llm_answer(raw)
        except LLMResponseError as second_error:
            raise LLMResponseError(
                f"Модель дважды вернула ответ в неверном формате: {second_error}."
            ) from second_error
