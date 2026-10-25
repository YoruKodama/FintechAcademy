"""Клиент локальной модели через HTTP API Ollama (/api/chat)."""

import json
import os
import urllib.error
import urllib.request

from ._common import with_russian_hint
from .base import LLMUnavailableError

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct"
TIMEOUT_SECONDS = 60


class OllamaClient:
    """Вызывает модель, запущенную локально в Ollama. Наружу ничего не отправляется."""

    def __init__(
        self,
        url: str | None = None,
        model: str | None = None,
        *,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        self.url = (url or os.getenv("OLLAMA_URL") or DEFAULT_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

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
        try:
            return self._request(payload)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            raise LLMUnavailableError(
                f"Модель Ollama недоступна по адресу {self.url}: {exc}"
            ) from exc

    def _request(self, payload: dict) -> str:
        request = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["message"]["content"]
