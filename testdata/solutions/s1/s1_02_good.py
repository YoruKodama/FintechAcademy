from decimal import Decimal, ROUND_HALF_UP


def calc_fee(amount):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("amount must be positive")
    fee = amount * Decimal("0.015")
    if fee < 30:
        fee = Decimal(30)
    if fee > 3000:
        fee = Decimal(3000)
    return fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
