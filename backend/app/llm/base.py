"""Интерфейс клиента языковой модели и ошибки LLM-слоя."""

from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Базовая ошибка работы с моделью. Текст ошибки понятен пользователю."""


class LLMUnavailableError(LLMError):
    """Модель недоступна: сервис не отвечает, нет ключа или сработал таймаут."""


class LLMConfigError(LLMError):
    """Неверная настройка: например, неизвестное значение LLM_PROVIDER."""


class LLMResponseError(LLMError):
    """Модель ответила, но ответ не соответствует ожидаемому формату."""


@runtime_checkable
class LLMClient(Protocol):
    """Единый интерфейс для всех провайдеров (заглушка, Ollama, GigaChat)."""

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> str:
        """Отправить системный и пользовательский текст, вернуть ответ модели."""
        ...
