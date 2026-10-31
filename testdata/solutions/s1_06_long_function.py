from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def calc_fee(amount):
    # Шаг 1. Приводим сумму к Decimal
    if isinstance(amount, float):
        raise ValueError("Сумма не должна быть float")
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        raise ValueError("Некорректная сумма")

    # Шаг 2. Проверяем сумму
    if not value.is_finite():
        raise ValueError("Сумма должна быть конечной")
    if value <= 0:
        raise ValueError("Сумма должна быть положительной")

    # Шаг 3. Считаем процент
    rate = Decimal("0.015")
    fee = value * rate

    # Шаг 4. Применяем минимум
    minimum = Decimal("30")
    if fee < minimum:
        fee = minimum

    # Шаг 5. Применяем максимум
    maximum = Decimal("3000")
    if fee > maximum:
        fee = maximum

    # Шаг 6. Округляем до копеек
    kopeck = Decimal("0.01")
    fee = fee.quantize(kopeck, rounding=ROUND_HALF_UP)

    # Шаг 7. Возвращаем результат
    return fee
