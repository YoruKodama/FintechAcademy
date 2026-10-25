def calc_fee(amount):
    if amount <= 0:
        raise ValueError("bad amount")
    fee = amount * 0.015
    if fee < 30:
        fee = 30
    if fee > 3000:
        fee = 3000
    return round(fee, 2)
