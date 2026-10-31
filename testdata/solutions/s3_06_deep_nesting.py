from decimal import Decimal, InvalidOperation


def process_statement(opening_balance, operations, limit=Decimal("100000")):
    balance = Decimal(str(opening_balance))
    large = []
    for op in operations:
        try:
            amount = Decimal(str(op["amount"]))
        except InvalidOperation:
            raise ValueError(f"Операция {op.get('id')}: некорректная сумма")
        if amount < 0:
            raise ValueError(f"Операция {op.get('id')}: отрицательная сумма")
        if op["type"] == "in":
            balance += amount
        else:
            if op["type"] == "out":
                balance -= amount
                if amount > 0:
                    if amount > limit:
                        large.append(op["id"])
            else:
                raise ValueError(f"Операция {op.get('id')}: неизвестный тип")
    return balance, large
