from decimal import Decimal


def process_statement(opening_balance, operations, limit=Decimal("100000")):
    balance = Decimal(opening_balance)
    big = []
    for op in operations:
        amount = Decimal(op["amount"])
        if amount < 0:
            raise ValueError("negative amount")
        if op["type"] == "in":
            balance += amount
        elif op["type"] == "out":
            balance -= amount
            if amount > limit:
                big.append(op["id"])
        else:
            raise ValueError("unknown type")
    return balance, big
