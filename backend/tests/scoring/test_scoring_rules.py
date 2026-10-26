"""Тесты правил баллов."""

from app.scoring.rules import (
    EMPTY_SOLUTION,
    apply_finding_rules,
    explanation_cap,
    is_empty_solution,
)


def finding(code: str, severity: str = "medium", line: int = 1) -> dict:
    return {"code": code, "severity": severity, "line": line, "message": "замечание"}


def test_no_findings_means_full_caps():
    outcome = apply_finding_rules([])
    assert outcome.caps == {"correctness": 25, "code_quality": 25, "safety": 25, "explanation": 25}
    assert outcome.applied == []


def test_float_money_reduces_safety():
    outcome = apply_finding_rules([finding("FLOAT_MONEY", "high")])
    assert outcome.caps["safety"] == 15
    assert outcome.caps["code_quality"] == 25
    assert outcome.applied == [("FLOAT_MONEY", "safety", 10)]


def test_each_code_counts_once():
    outcome = apply_finding_rules([finding("FLOAT_MONEY", line=3), finding("FLOAT_MONEY", line=9)])
    assert outcome.caps["safety"] == 15


def test_several_rules_add_up_and_never_go_below_zero():
    findings = [finding("FLOAT_MONEY"), finding("NO_VALIDATION"), finding("HARDCODED_SECRET")]
    assert apply_finding_rules(findings).caps["safety"] == 0


def test_syntax_error_zeroes_correctness():
    assert apply_finding_rules([finding("SYNTAX_ERROR", "high")]).caps["correctness"] == 0


def test_unknown_code_uses_severity_for_code_quality():
    findings = [
        finding("LONG_FUNCTION", "high"),
        finding("MAGIC_NUMBER", "low"),
        finding("X", "weird"),
    ]
    outcome = apply_finding_rules(findings)
    assert outcome.caps["code_quality"] == 25 - 6 - 1 - 1


def test_empty_solution_detection():
    assert is_empty_solution([finding(EMPTY_SOLUTION, "high")])
    assert not is_empty_solution([finding("FLOAT_MONEY")])
    assert not is_empty_solution([])


def test_explanation_cap_by_answers():
    long_answer = "Я использую Decimal, потому что float теряет точность при суммах в копейках."
    assert explanation_cap([]) == 0
    assert explanation_cap(["", "   "]) == 0
    assert explanation_cap(["да", "не знаю"]) == 10
    assert explanation_cap([long_answer, "ок"]) == 10
    assert explanation_cap([long_answer, "Так безопаснее для денег клиента."]) == 25
    assert explanation_cap([long_answer, long_answer]) == 25
