"""Правила анализатора: по одному модулю на правило, у каждого функция check(tree, source)."""

from . import (
    bare_except,
    deep_nesting,
    eval_exec,
    float_money,
    long_function,
    missing_return,
    no_input_validation,
    unused_variable,
)

ALL_RULES = (
    float_money,
    bare_except,
    eval_exec,
    no_input_validation,
    long_function,
    unused_variable,
    deep_nesting,
    missing_return,
)

__all__ = ["ALL_RULES"]
