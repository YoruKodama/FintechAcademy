"""Тесты правил анализатора: на каждое правило замечание есть и ложных срабатываний нет."""

import pytest

from app.analysis import analyze

GOOD = '''\
from decimal import Decimal


def calc_fee(amount):
    """Вернуть комиссию."""
    value = Decimal(str(amount))
    if value <= 0:
        raise ValueError("Сумма должна быть положительной")
    return value * Decimal("0.015")
'''


def codes(source: str) -> set[str]:
    return {item["code"] for item in analyze(source)}


def test_good_code_has_no_findings():
    assert analyze(GOOD) == []


def test_finding_has_contract_shape():
    item = analyze("x = 0.5\n")[0]
    assert set(item) == {"code", "severity", "line", "message"}
    assert item["severity"] in {"low", "medium", "high"}
    assert item["line"] >= 1
    assert item["message"]


def test_float_money_literal_and_call():
    found = analyze("def f(a):\n    fee = a * 0.015\n    return float(fee)\n")
    assert [(i["code"], i["line"]) for i in found if i["code"] == "FLOAT_MONEY"] == [
        ("FLOAT_MONEY", 2),
        ("FLOAT_MONEY", 3),
    ]


def test_bare_except_and_broad_except():
    source = "try:\n    pass\nexcept:\n    pass\ntry:\n    pass\nexcept Exception:\n    pass\n"
    found = [i for i in analyze(source) if i["code"] == "BARE_EXCEPT"]
    assert [(i["line"], i["severity"]) for i in found] == [(3, "medium"), (7, "low")]


def test_specific_except_is_fine():
    assert "BARE_EXCEPT" not in codes("try:\n    pass\nexcept ValueError:\n    pass\n")


@pytest.mark.parametrize("call", ["eval", "exec"])
def test_eval_exec(call):
    found = [i for i in analyze(f"{call}('1+1')\n") if i["code"] == "EVAL_EXEC"]
    assert len(found) == 1
    assert found[0]["severity"] == "high"


def test_no_input_validation_flagged_and_cleared():
    assert "NO_INPUT_VALIDATION" in codes("def f(a):\n    return a\n")
    assert "NO_INPUT_VALIDATION" not in codes(
        "def f(a):\n    if a < 0:\n        raise ValueError\n    return a\n"
    )
    assert "NO_INPUT_VALIDATION" not in codes("def f(a):\n    assert a\n    return a\n")
    assert "NO_INPUT_VALIDATION" not in codes("def f(a):\n    return isinstance(a, int)\n")


def test_no_input_validation_ignores_functions_without_params():
    assert "NO_INPUT_VALIDATION" not in codes("def f():\n    return 1\n")


def test_long_function():
    body = "\n".join(f"    x{i} = {i}" for i in range(35))
    source = f"def f():\n{body}\n    return x0\n"
    found = [i for i in analyze(source) if i["code"] == "LONG_FUNCTION"]
    assert [i["line"] for i in found] == [1]


def test_short_function_is_fine():
    assert "LONG_FUNCTION" not in codes(GOOD)


def test_unused_variable():
    found = [
        i
        for i in analyze("def f():\n    tmp = 1\n    return 2\n")
        if i["code"] == "UNUSED_VARIABLE"
    ]
    assert [(i["line"], "tmp" in i["message"]) for i in found] == [(2, True)]


def test_used_and_underscore_variables_are_fine():
    assert "UNUSED_VARIABLE" not in codes("def f():\n    a = 1\n    _b = 2\n    return a\n")


def test_deep_nesting():
    source = (
        "def f(items):\n"
        "    for a in items:\n"
        "        if a:\n"
        "            for b in a:\n"
        "                if b:\n"
        "                    return b\n"
        "    return None\n"
    )
    found = [i for i in analyze(source) if i["code"] == "DEEP_NESTING"]
    assert [i["line"] for i in found] == [5]


def test_nesting_of_three_is_fine():
    source = (
        "def f(items):\n    for a in items:\n        if a:\n            return a\n    return None\n"
    )
    assert "DEEP_NESTING" not in codes(source)


def test_missing_return_in_branch():
    source = "def f(x):\n    if x:\n        return 1\n"
    found = [i for i in analyze(source) if i["code"] == "MISSING_RETURN"]
    assert len(found) == 1


@pytest.mark.parametrize(
    "source",
    [
        "def f(x):\n    if x:\n        return 1\n    return 2\n",
        "def f(x):\n    if x:\n        return 1\n    else:\n        raise ValueError\n",
        "def f(x):\n    try:\n        return 1\n    except ValueError:\n        return 2\n",
        "def f(x):\n    print(x)\n",
    ],
)
def test_return_on_all_paths_is_fine(source):
    assert "MISSING_RETURN" not in codes(source)


@pytest.mark.parametrize("source", ["", "   \n", "просто текст, а не код", "def (:\n"])
def test_not_python_does_not_crash(source):
    result = analyze(source)
    assert isinstance(result, list)


def test_syntax_error_becomes_finding():
    found = analyze("def f(:\n    pass\n")
    assert [i["code"] for i in found] == ["SYNTAX_ERROR"]


def test_very_long_code_is_skipped():
    found = analyze("x = 1\n" * 10_000)
    assert [i["code"] for i in found] == ["CODE_TOO_LONG"]


def test_findings_sorted_by_line():
    source = "def f(a):\n    x = 0.5\n    return eval(a)\n"
    lines = [i["line"] for i in analyze(source)]
    assert lines == sorted(lines)
