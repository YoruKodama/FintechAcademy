"""Адаптер GigaChat (российская облачная модель). Тот же интерфейс, что у остальных клиентов.

Ключи берутся только из переменных окружения. Без ключа клиент создаётся без ошибок
и падает с понятным сообщением только при вызове, поэтому запуск проекта не ломается.
"""

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable

from ._common import with_russian_hint
from .base import LLMUnavailableError

logger = logging.getLogger(__name__)

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
DEFAULT_SCOPE = "GIGACHAT_API_PERS"
DEFAULT_MODEL = "GigaChat"
TIMEOUT_SECONDS = 60
TOKEN_RESERVE_SECONDS = 60


class GigaChatClient:
    """Вызывает GigaChat по HTTP: получает токен по ключу авторизации и отправляет запрос."""

    def __init__(
        self,
        credentials: str | None = None,
        model: str | None = None,
        scope: str | None = None,
        *,
        ca_bundle: str | None = None,
        timeout: float = TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.credentials = credentials or os.getenv("GIGACHAT_CREDENTIALS") or ""
        self.model = model or os.getenv("GIGACHAT_MODEL") or DEFAULT_MODEL
        self.scope = scope or os.getenv("GIGACHAT_SCOPE") or DEFAULT_SCOPE
        self.ca_bundle = ca_bundle or os.getenv("GIGACHAT_CA_BUNDLE") or None
        self.timeout = timeout
        self._clock = clock
        self._token: str | None = None
        self._token_expires_at = 0.0

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> str:
        if not self.credentials:
            raise LLMUnavailableError(
                "GigaChat не настроен: задайте ключ авторизации в переменной окружения "
                "GIGACHAT_CREDENTIALS или выберите другой LLM_PROVIDER."
            )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": with_russian_hint(system)},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        body = self._chat(payload)
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMUnavailableError("GigaChat вернул ответ в неожиданном формате.") from None
        if not isinstance(content, str) or not content.strip():
            raise LLMUnavailableError("GigaChat вернул пустой ответ.")
        return content

    def _chat(self, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        try:
            return self._post(CHAT_URL, data, self._chat_headers())
        except urllib.error.HTTPError as exc:
            if exc.code != 401:
                raise self._http_error(exc) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise self._network_error(exc) from exc
        self._token = None
        try:
            return self._post(CHAT_URL, data, self._chat_headers())
        except urllib.error.HTTPError as exc:
            raise self._http_error(exc) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise self._network_error(exc) from exc

    def _chat_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_token(self) -> str:
        if self._token and self._clock() < self._token_expires_at - TOKEN_RESERVE_SECONDS:
            return self._token
        headers = {
            "Authorization": f"Basic {self.credentials}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = urllib.parse.urlencode({"scope": self.scope}).encode("utf-8")
        try:
            body = self._post(AUTH_URL, data, headers)
            self._token = body["access_token"]
            self._token_expires_at = float(body["expires_at"]) / 1000
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 401, 403):
                raise LLMUnavailableError(
                    "GigaChat отклонил ключ авторизации. "
                    "Проверьте GIGACHAT_CREDENTIALS и GIGACHAT_SCOPE."
                ) from exc
            raise self._http_error(exc) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise self._network_error(exc) from exc
        except (KeyError, TypeError, ValueError):
            raise LLMUnavailableError("GigaChat вернул токен в неожиданном формате.") from None
        return self._token

    def _post(self, url: str, data: bytes, headers: dict[str, str]) -> dict:
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        context = ssl.create_default_context(cafile=self.ca_bundle)
        with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))

    def _http_error(self, exc: urllib.error.HTTPError) -> LLMUnavailableError:
        if exc.code == 429:
            return LLMUnavailableError("GigaChat: превышен лимит запросов, попробуйте позже.")
        return LLMUnavailableError(f"GigaChat вернул ошибку (код {exc.code}).")

    def _network_error(self, exc: Exception) -> LLMUnavailableError:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, ssl.SSLError):
            return LLMUnavailableError(
                "GigaChat: не удалось проверить сертификат. Укажите файл корневого сертификата "
                "Минцифры в переменной GIGACHAT_CA_BUNDLE."
            )
        return LLMUnavailableError(f"GigaChat недоступен: {reason}.")
