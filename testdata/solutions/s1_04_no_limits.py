def calc_fee(amount):
    try:
        return round(float(amount) * 1.5 / 100, 2)
    except:
        return 0
