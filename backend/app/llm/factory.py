"""Выбор клиента модели по переменной окружения LLM_PROVIDER."""

import os

from .base import LLMClient, LLMConfigError

DEFAULT_PROVIDER = "stub"


def _make_stub() -> LLMClient:
    from .stub import StubClient

    return StubClient()


_PROVIDERS = {
    "stub": _make_stub,
}


def get_llm_client() -> LLMClient:
    """Вернуть клиента модели для текущего LLM_PROVIDER (по умолчанию stub)."""
    provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    try:
        factory = _PROVIDERS[provider]
    except KeyError:
        available = ", ".join(sorted(_PROVIDERS))
        raise LLMConfigError(
            f"Неизвестный провайдер модели LLM_PROVIDER={provider!r}. Доступно: {available}."
        ) from None
    return factory()
