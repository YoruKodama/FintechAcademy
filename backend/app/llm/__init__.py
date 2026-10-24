"""LLM-слой: вызов языковой модели через единый интерфейс."""

from .base import (
    LLMClient,
    LLMConfigError,
    LLMError,
    LLMResponseError,
    LLMUnavailableError,
)
from .factory import get_llm_client
from .types import Finding, Result

__all__ = [
    "Finding",
    "LLMClient",
    "LLMConfigError",
    "LLMError",
    "LLMResponseError",
    "LLMUnavailableError",
    "Result",
    "get_llm_client",
]
