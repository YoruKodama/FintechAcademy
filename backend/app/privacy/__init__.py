"""Обезличивание персональных данных до отправки текста в модель."""

from .anonymize import anonymize, deanonymize

__all__ = ["anonymize", "deanonymize"]
