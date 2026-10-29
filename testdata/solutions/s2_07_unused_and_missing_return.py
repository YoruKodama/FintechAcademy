def is_valid_card(number):
    if not isinstance(number, str):
        raise ValueError("Номер карты должен быть строкой")
    digits = number.replace(" ", "").replace("-", "")
    checked = False
    if digits.isdigit() and 16 <= len(digits) <= 19:
        total = 0
        for index, char in enumerate(reversed(digits)):
            value = int(char)
            if index % 2 == 1:
                value = value * 2 - 9 if value > 4 else value * 2
            total += value
        return total % 10 == 0


def mask_card(number):
    if not is_valid_card(number):
        raise ValueError("Некорректный номер карты")
    return "**** **** **** " + number.replace(" ", "").replace("-", "")[-4:]
