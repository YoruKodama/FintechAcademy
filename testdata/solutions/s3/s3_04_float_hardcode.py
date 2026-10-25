def process_statement(opening_balance, operations, limit=None):
    balance = float(opening_balance)
    big = []
    for op in operations:
        try:
            a = float(op["amount"])
            if op["type"] == "in":
                balance += a
            if op["type"] == "out":
                balance -= a
                if a > 100000:
                    big.append(op["id"])
        except Exception:
            continue
    return balance, big
