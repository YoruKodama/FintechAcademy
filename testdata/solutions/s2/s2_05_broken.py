def is_valid_card(number):
    while True:
        try:
            return int(number) % 10 == 0
        except:
            pass


def mask_card(number):
    return number
