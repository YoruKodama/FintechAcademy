from decimal import Decimal


def process_statement(opening_balance, operations, limit=Decimal("100000"), big=[]):
    balance = Decimal(opening_balance)
    for op in operations:
        op["amount"] = Decimal(op["amount"])
        if op["type"] == "in":
            balance += op["amount"]
        else:
            balance -= op["amount"]
            if op["amount"] > limit:
                big.append(op["id"])
    return balance, big
