from decimal import ROUND_HALF_UP, Decimal


def calc_fee(amount):
    value = Decimal(str(amount))
    if value <= 0:
        raise ValueError("Сумма должна быть положительной")
    fee = (value * Decimal("0.015")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if fee < 30:
        return Decimal("30.00")
    if fee > 3000:
        return Decimal("3000.00")
    if fee >= 30:
        return fee
