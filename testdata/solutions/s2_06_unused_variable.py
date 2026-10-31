def _clean(number):
    if not isinstance(number, str):
        raise ValueError("Номер карты должен быть строкой")
    return number.replace(" ", "").replace("-", "")


def is_valid_card(number):
    try:
        digits = _clean(number)
    except ValueError:
        return False
    length = len(digits)
    first_digit = digits[:1]
    if not digits.isdigit() or not 16 <= len(digits) <= 19:
        return False
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        doubled = value * 2
        if index % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def mask_card(number):
    if not is_valid_card(number):
        raise ValueError("Некорректный номер карты")
    return "**** **** **** " + _clean(number)[-4:]
