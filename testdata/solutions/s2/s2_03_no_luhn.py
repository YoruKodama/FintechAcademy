def is_valid_card(number):
    digits = number.replace(" ", "")
    return digits.isdigit() and len(digits) == 16


def mask_card(number):
    digits = number.replace(" ", "")
    return "**** **** **** " + digits[-4:]
