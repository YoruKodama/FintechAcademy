"""Обезличивание текста перед отправкой в модель.

Заменяет e-mail, номера карт, телефоны и ФИО на метки вида [ТЕЛЕФОН_1].
Одно и то же значение всегда получает одну и ту же метку.
"""

import re

from .names import NAME, PATRONYMIC, SURNAME_STRONG, SURNAME_WEAK, classify

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")

_CARD_GROUPED = re.compile(r"(?<![\w.\-])\d{4}[ \-]\d{4}[ \-]\d{4}[ \-]\d{1,7}(?![\w\-])")
_CARD_PLAIN = re.compile(r"(?<![\w.])\d{16,19}(?![\w.])")

_PHONE_RU = re.compile(
    r"(?<![\w.+\-])(?:\+7|\+?8|7)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
)
_PHONE_INTL = re.compile(r"(?<![\w+])\+\d[\d\s\-()]{8,16}\d(?!\d)")

_WORD = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)*"
_SPACE = r"[ \u00a0]"
_RUN = re.compile(rf"(?<![\w\-]){_WORD}(?:{_SPACE}{_WORD})*(?![\w\-])")
_WORD_RE = re.compile(_WORD)
_INITIALS_AFTER = re.compile(rf"(?<![\w\-])({_WORD}){_SPACE}+[А-ЯЁ]\.(?:{_SPACE}?[А-ЯЁ]\.)?")
_INITIALS_BEFORE = re.compile(
    rf"(?<![\w\-])[А-ЯЁ]\.(?:{_SPACE}?[А-ЯЁ]\.)?{_SPACE}?({_WORD})(?![\w\-])"
)
_CUE = re.compile(
    r"(?i:\b(?:меня зовут|зовут|клиент\w*|сотрудник\w*|владел\w+|получател\w+|отправител\w+"
    r"|пользовател\w+|менеджер\w*|фио|имя|фамилия)\b)"
    rf"[ \t]*[:\-—]?[ \t]*(?P<words>{_WORD}(?:{_SPACE}{_WORD}){{0,2}})"
)
_MAX_NAME_WORDS = 3


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


def _is_person(kinds: list[str | None]) -> bool:
    """Подходит ли набор подряд идущих слов под ФИО."""
    if len(kinds) < 2 or None in kinds:
        return False
    has_name_part = NAME in kinds or PATRONYMIC in kinds
    return has_name_part and set(kinds) != {NAME}


def _mask_initials(text: str, labeler: _Labeler) -> str:
    def replace(match: re.Match) -> str:
        if classify(match.group(1)) not in (SURNAME_STRONG, SURNAME_WEAK, PATRONYMIC):
            return match.group(0)
        return labeler.label("ФИО", match.group(0))

    text = _INITIALS_AFTER.sub(replace, text)
    return _INITIALS_BEFORE.sub(replace, text)


def _mask_after_cue(text: str, labeler: _Labeler) -> str:
    standalone = (NAME, PATRONYMIC, SURNAME_STRONG)

    def replace(match: re.Match) -> str:
        words = list(_WORD_RE.finditer(match.group("words")))
        taken = 0
        for word in words[:_MAX_NAME_WORDS]:
            if classify(word.group(0)) not in standalone:
                break
            taken += 1
        if not taken:
            return match.group(0)
        start = match.start("words") - match.start()
        end = start + words[taken - 1].end()
        value = match.group(0)[start:end]
        return match.group(0)[:start] + labeler.label("ФИО", value) + match.group(0)[end:]

    return _CUE.sub(replace, text)


def _mask_name_runs(text: str, labeler: _Labeler) -> str:
    def replace(match: re.Match) -> str:
        run = match.group(0)
        words = list(_WORD_RE.finditer(run))
        kinds = [classify(word.group(0)) for word in words]
        pieces: list[str] = []
        position = 0
        index = 0
        while index < len(words):
            size = min(_MAX_NAME_WORDS, len(words) - index)
            while size >= 2 and not _is_person(kinds[index : index + size]):
                size -= 1
            if size < 2:
                index += 1
                continue
            start, end = words[index].start(), words[index + size - 1].end()
            pieces.append(run[position:start])
            pieces.append(labeler.label("ФИО", run[start:end]))
            position = end
            index += size
        pieces.append(run[position:])
        return "".join(pieces)

    return _RUN.sub(replace, text)


def anonymize(text: str) -> tuple[str, dict[str, str]]:
    """Заменить персональные данные метками.

    Возвращает обезличенный текст и словарь «метка -> исходное значение».
    Словарь остаётся у нас и в модель не отправляется.
    """
    labeler = _Labeler()
    text = _mask_emails(text, labeler)
    text = _mask_cards(text, labeler)
    text = _mask_phones(text, labeler)
    text = _mask_initials(text, labeler)
    text = _mask_after_cue(text, labeler)
    text = _mask_name_runs(text, labeler)
    return text, labeler.mapping


def deanonymize(text: str, mapping: dict[str, str]) -> str:
    """Вернуть исходные значения вместо меток (например, в ответе, который увидит пользователь)."""
    for label, value in mapping.items():
        text = text.replace(label, value)
    return text
