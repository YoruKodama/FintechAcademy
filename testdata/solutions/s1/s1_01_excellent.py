"""Комиссия за перевод: 1,5 %, минимум 30 ₽, максимум 3000 ₽."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

FEE_RATE = Decimal("0.015")
MIN_FEE = Decimal("30")
MAX_FEE = Decimal("3000")
KOPECK = Decimal("0.01")


def calc_fee(amount: Decimal | int | str) -> Decimal:
    """Вернуть комиссию в рублях с точностью до копейки."""
    if isinstance(amount, float):
        raise ValueError("Сумму передавайте как Decimal или строку, не float")
    try:
        value = Decimal(str(amount))
    except InvalidOperation as exc:
        raise ValueError(f"Некорректная сумма: {amount!r}") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError("Сумма перевода должна быть положительной")
    fee = min(max(value * FEE_RATE, MIN_FEE), MAX_FEE)
    return fee.quantize(KOPECK, rounding=ROUND_HALF_UP)
