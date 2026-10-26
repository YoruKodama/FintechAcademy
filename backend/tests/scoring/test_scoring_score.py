"""Тесты score(): воспроизводимость, границы 0..100 и крайние случаи."""

import json

import pytest

from app.llm.parsing import LLMAnswer
from app.scoring.scorer import NO_MODEL_SCORE, score

LONG_ANSWERS = [
    "Я храню деньги в Decimal, потому что float теряет точность при расчётах с копейками.",
    "Проверяю, что сумма положительная и на счёте хватает средств, иначе выбрасываю ошибку.",
]


def finding(code: str, severity: str = "medium", line: int = 1) -> dict:
    return {"code": code, "severity": severity, "line": line, "message": "замечание"}


def model(correctness=25, code_quality=25, safety=25, explanation=25, feedback="Хороший разбор."):
    return LLMAnswer(
        criteria={
            "correctness": correctness,
            "code_quality": code_quality,
            "safety": safety,
            "explanation": explanation,
        },
        feedback=feedback,
    )


def test_same_input_gives_same_result_three_runs():
    findings = [finding("FLOAT_MONEY", "high", 4), finding("LONG_FUNCTION", "low", 10)]
    answer = model(20, 18, 14, 22)
    results = [score(findings, answer, LONG_ANSWERS) for _ in range(3)]
    assert results[0] == results[1] == results[2]


def test_raw_json_string_gives_same_result_as_parsed_answer():
    raw = json.dumps(
        {
            "criteria": {"correctness": 20, "code_quality": 18, "safety": 14, "explanation": 22},
            "feedback": "ок",
        },
        ensure_ascii=False,
    )
    parsed = LLMAnswer(criteria=json.loads(raw)["criteria"], feedback="ок")
    assert score([], raw, LONG_ANSWERS) == score([], parsed, LONG_ANSWERS)


def test_no_findings_and_perfect_model_gives_100():
    result = score([], model(), LONG_ANSWERS)
    assert result["total"] == 100
    assert result["criteria"] == {
        "correctness": 25,
        "code_quality": 25,
        "safety": 25,
        "explanation": 25,
    }
    assert result["feedback"] == "Хороший разбор."
    assert result["findings"] == []


def test_float_money_takes_points_from_safety_even_if_model_is_generous():
    result = score([finding("FLOAT_MONEY", "high", 7)], model(), LONG_ANSWERS)
    assert result["criteria"]["safety"] == 15
    assert result["total"] == 90
    assert "FLOAT_MONEY" in result["feedback"]
    assert result["findings"][0]["line"] == 7


def test_model_can_lower_but_not_raise_above_rules():
    result = score([finding("FLOAT_MONEY")], model(safety=5), LONG_ANSWERS)
    assert result["criteria"]["safety"] == 5


def test_empty_solution_gives_zero():
    result = score([finding("EMPTY_SOLUTION", "high", 1)], model(), LONG_ANSWERS)
    assert result["total"] == 0
    assert set(result["criteria"].values()) == {0}
    assert "пустое" in result["feedback"]


def test_empty_answers_zero_explanation():
    result = score([], model(), ["", "  "])
    assert result["criteria"]["explanation"] == 0
    assert result["total"] == 75


@pytest.mark.parametrize(
    "broken",
    [
        "",
        "это не JSON",
        "{не закрыт",
        '{"criteria": {"correctness": 1}, "feedback": "мало ключей"}',
        None,
    ],
)
def test_broken_or_missing_model_answer_falls_back_to_rules(broken):
    result = score([finding("FLOAT_MONEY")], broken, LONG_ANSWERS)
    assert result["criteria"]["correctness"] == NO_MODEL_SCORE
    assert result["criteria"]["explanation"] == NO_MODEL_SCORE
    assert result["criteria"]["safety"] == 15
    assert result["criteria"]["code_quality"] == 25
    assert 0 <= result["total"] <= 100
    assert "Подробный разбор от модели получить не удалось" in result["feedback"]


def test_out_of_range_model_values_are_clamped():
    result = score([], model(correctness=99, code_quality=-4), LONG_ANSWERS)
    assert result["criteria"]["correctness"] == 25
    assert result["criteria"]["code_quality"] == 0


def test_total_always_between_0_and_100():
    codes = [
        "FLOAT_MONEY",
        "NO_VALIDATION",
        "HARDCODED_SECRET",
        "SYNTAX_ERROR",
        "BARE_EXCEPT",
        "OTHER",
    ]
    findings = [finding(code, "high") for code in codes]
    for answers in ([], ["да"], LONG_ANSWERS):
        for answer in (None, model(), model(0, 0, 0, 0), "мусор"):
            total = score(findings, answer, answers)["total"]
            assert 0 <= total <= 100


def test_total_equals_sum_of_criteria():
    result = score([finding("NO_VALIDATION")], model(20, 17, 25, 21), LONG_ANSWERS)
    assert result["total"] == sum(result["criteria"].values())


def test_feedback_never_exceeds_limit_and_keeps_rules_note():
    long_feedback = "Очень подробный разбор. " * 200
    findings = [finding("FLOAT_MONEY"), finding("NO_VALIDATION")]
    result = score(findings, model(feedback=long_feedback), LONG_ANSWERS)
    assert len(result["feedback"]) <= 1200
    assert "Снято автоматическими правилами" in result["feedback"]
    assert "FLOAT_MONEY" in result["feedback"] and "NO_VALIDATION" in result["feedback"]


def test_score_does_not_modify_input():
    findings = [finding("FLOAT_MONEY")]
    snapshot = json.dumps(findings)
    score(findings, model(), LONG_ANSWERS)
    assert json.dumps(findings) == snapshot
