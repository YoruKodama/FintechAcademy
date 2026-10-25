"""Обезличивание текста перед отправкой в модель.

Заменяет e-mail, номера карт и телефоны на метки вида [ТЕЛЕФОН_1].
Одно и то же значение всегда получает одну и ту же метку.
"""

import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")

_CARD_GROUPED = re.compile(r"(?<![\w.\-])\d{4}[ \-]\d{4}[ \-]\d{4}[ \-]\d{1,7}(?![\w\-])")
_CARD_PLAIN = re.compile(r"(?<![\w.])\d{16,19}(?![\w.])")

_PHONE_RU = re.compile(
    r"(?<![\w.+\-])(?:\+7|\+?8|7)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
)
_PHONE_INTL = re.compile(r"(?<![\w+])\+\d[\d\s\-()]{8,16}\d(?!\d)")


class _Labeler:
    """Выдаёт метки [ВИД_N] и хранит соответствие метка -> исходное значение."""

    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self._labels: dict[tuple[str, str], str] = {}
        self._counts: dict[str, int] = {}

    def label(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self._labels:
            number = self._counts.get(kind, 0) + 1
            self._counts[kind] = number
            label = f"[{kind}_{number}]"
            self._labels[key] = label
            self.mapping[label] = value
        return self._labels[key]


def _luhn_ok(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        number = int(char)
        if index % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _mask_emails(text: str, labeler: _Labeler) -> str:
    return _EMAIL.sub(lambda m: labeler.label("EMAIL", m.group(0)), text)


def _mask_cards(text: str, labeler: _Labeler) -> str:
    text = _CARD_GROUPED.sub(lambda m: labeler.label("КАРТА", m.group(0)), text)

    def plain(match: re.Match) -> str:
        value = match.group(0)
        return labeler.label("КАРТА", value) if _luhn_ok(value) else value

    return _CARD_PLAIN.sub(plain, text)


def _mask_phones(text: str, labeler: _Labeler) -> str:
    def russian(match: re.Match) -> str:
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) != 11 or digits[0] not in "78":
            return raw
        if re.fullmatch(r"\d+", raw) and digits[1] != "9":
            return raw
        return labeler.label("ТЕЛЕФОН", raw)

    def international(match: re.Match) -> str:
        raw = match.group(0)
        if not 10 <= len(re.sub(r"\D", "", raw)) <= 15:
            return raw
        return labeler.label("ТЕЛЕФОН", raw)

    text = _PHONE_RU.sub(russian, text)
    return _PHONE_INTL.sub(international, text)


def anonymize(text: str) -> tuple[str, dict[str, str]]:
    """Заменить персональные данные метками.

    Возвращает обезличенный текст и словарь «метка -> исходное значение».
    Словарь остаётся у нас и в модель не отправляется.
    """
    labeler = _Labeler()
    text = _mask_emails(text, labeler)
    text = _mask_cards(text, labeler)
    text = _mask_phones(text, labeler)
    return text, labeler.mapping


def deanonymize(text: str, mapping: dict[str, str]) -> str:
    """Вернуть исходные значения вместо меток (например, в ответе, который увидит пользователь)."""
    for label, value in mapping.items():
        text = text.replace(label, value)
    return text
