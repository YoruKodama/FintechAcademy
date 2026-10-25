import os


def calc_fee(amount):
    # считаем комиссию через eval, чтобы поддержать выражения вида "100+200"
    value = eval(str(amount))
    print("fee for", value)
    os.system("echo calc >> /tmp/fee.log")
    return value * 0.015
