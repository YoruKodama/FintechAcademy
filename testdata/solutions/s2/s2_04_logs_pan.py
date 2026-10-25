import logging

log = logging.getLogger(__name__)


def is_valid_card(number):
    log.info("checking card %s", number)
    s = 0
    digits = [int(c) for c in number if c.isdigit()]
    for i in range(len(digits)):
        d = digits[len(digits) - 1 - i]
        if i % 2 == 1:
            d = d * 2
        s += d
    return s % 10 == 0


def mask_card(number):
    return number[:-4] + "****"
