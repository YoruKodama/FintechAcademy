"""Итоговый баланс по выписке и список крупных расходных операций."""

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation

DEFAULT_LIMIT = Decimal("100000")


def _amount(raw: object, op_id: object) -> Decimal:
    try:
        value = Decimal(str(raw))
    except InvalidOperation as exc:
        raise ValueError(f"Операция {op_id}: некорректная сумма {raw!r}") from exc
    if not value.is_finite() or value < 0:
        raise ValueError(f"Операция {op_id}: сумма должна быть неотрицательной")
    return value


def process_statement(
    opening_balance: Decimal,
    operations: Iterable[Mapping[str, str]],
    limit: Decimal = DEFAULT_LIMIT,
) -> tuple[Decimal, list[str]]:
    balance = Decimal(str(opening_balance))
    large: list[str] = []
    for op in operations:
        amount = _amount(op.get("amount"), op.get("id"))
        kind = op.get("type")
        if kind == "in":
            balance += amount
        elif kind == "out":
            balance -= amount
            if amount > limit:
                large.append(op["id"])
        else:
            raise ValueError(f"Операция {op.get('id')}: неизвестный тип {kind!r}")
    return balance, large
