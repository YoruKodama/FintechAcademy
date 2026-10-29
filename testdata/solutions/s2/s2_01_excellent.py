"""Проверка номера карты по алгоритму Луна и маскирование."""

import re

_ALLOWED = re.compile(r"[\d\s\-]+")


def _digits(number: str) -> str:
    if not isinstance(number, str) or not _ALLOWED.fullmatch(number):
        raise ValueError("Номер карты должен состоять из цифр, пробелов и дефисов")
    return re.sub(r"[\s\-]", "", number)


def _luhn(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def is_valid_card(number: str) -> bool:
    try:
        digits = _digits(number)
    except ValueError:
        return False
    return 16 <= len(digits) <= 19 and _luhn(digits)


def mask_card(number: str) -> str:
    if not is_valid_card(number):
        raise ValueError("Некорректный номер карты")
    return "**** **** **** " + _digits(number)[-4:]
