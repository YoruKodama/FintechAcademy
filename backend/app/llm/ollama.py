"""Клиент локальной модели через HTTP API Ollama (/api/chat)."""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from ._common import with_russian_hint
from .base import LLMError, LLMUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct"
TIMEOUT_SECONDS = 60
RETRIES = 2
RETRY_PAUSE_SECONDS = 1.0


class _RetryableError(Exception):
    """Временный сбой: запрос можно повторить."""


class OllamaClient:
    """Вызывает модель, запущенную локально в Ollama. Наружу ничего не отправляется."""

    def __init__(
        self,
        url: str | None = None,
        model: str | None = None,
        *,
        timeout: float = TIMEOUT_SECONDS,
        retries: int = RETRIES,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.url = (url or os.getenv("OLLAMA_URL") or DEFAULT_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout = timeout
        self.retries = retries
        self._sleep = sleep

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": with_russian_hint(system)},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return self._request(payload)
            except _RetryableError as exc:
                last_error = exc
                logger.warning(
                    "Ollama: попытка %d из %d не удалась: %s", attempt + 1, self.retries + 1, exc
                )
                if attempt < self.retries:
                    self._sleep(RETRY_PAUSE_SECONDS * (attempt + 1))
        raise LLMUnavailableError(
            f"Модель Ollama недоступна по адресу {self.url}: {last_error}. "
            f"Проверьте, что сервис запущен и модель {self.model} загружена (ollama pull)."
        )

    def _request(self, payload: dict) -> str:
        request = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LLMError(
                    f"Модель {self.model} не найдена в Ollama. Выполните: ollama pull {self.model}"
                ) from exc
            if exc.code >= 500:
                raise _RetryableError(f"ошибка сервера {exc.code}") from exc
            raise LLMError(f"Ollama отклонила запрос (код {exc.code}).") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise _RetryableError(str(getattr(exc, "reason", exc))) from exc
        except ValueError as exc:
            raise _RetryableError("ответ не является корректным JSON") from exc

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise _RetryableError("в ответе нет поля message.content") from exc
        if not isinstance(content, str) or not content.strip():
            raise _RetryableError("модель вернула пустой ответ")
        return content
