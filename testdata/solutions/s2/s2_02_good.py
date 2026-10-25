def is_valid_card(number):
    digits = number.replace(" ", "").replace("-", "")
    if not digits.isdigit() or not 16 <= len(digits) <= 19:
        return False
    total = 0
    for i, ch in enumerate(digits[::-1]):
        d = int(ch)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def mask_card(number):
    if not is_valid_card(number):
        raise ValueError("invalid card")
    digits = number.replace(" ", "").replace("-", "")
    return "**** **** **** " + digits[-4:]
