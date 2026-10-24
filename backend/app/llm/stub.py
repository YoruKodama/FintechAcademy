"""Заглушка модели: заранее заданные ответы, без сети."""

import json

DEFAULT_TEXT = (
    "Заглушка модели: решение получено. "
    "Подробный разбор появится после подключения настоящей модели."
)

DEFAULT_JSON = json.dumps(
    {
        "criteria": {
            "correctness": 18,
            "code_quality": 17,
            "safety": 15,
            "explanation": 16,
        },
        "feedback": (
            "Решение в целом верное, логика читается. "
            "Стоит добавить проверки входных данных и не хранить деньги в float."
        ),
    },
    ensure_ascii=False,
)


class StubClient:
    """Возвращает заготовленный текст или JSON и ничего не отправляет по сети.

    Если в системном промпте упоминается JSON, отдаётся `json_answer`,
    иначе `text`. Все вызовы сохраняются в `calls` для проверок в тестах.
    """

    def __init__(self, text: str = DEFAULT_TEXT, json_answer: str = DEFAULT_JSON) -> None:
        self.text = text
        self.json_answer = json_answer
        self.calls: list[dict] = []

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.json_answer if "json" in system.lower() else self.text
