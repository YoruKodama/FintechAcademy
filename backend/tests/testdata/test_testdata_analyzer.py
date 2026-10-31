"""Анализатор находит в тестовых решениях замечания из expected.csv.

Полнота: каждое ожидаемое замечание (код и severity) найдено.
Точность: лишних кодов нет. Известные ложные срабатывания анализатора отмечены xfail.
"""

import csv
from pathlib import Path

import pytest

from app.analysis import analyze

SOLUTIONS = Path(__file__).resolve().parents[3] / "testdata" / "solutions"
ROWS = list(csv.DictReader((SOLUTIONS / "expected.csv").open(encoding="utf-8")))

# Ложные срабатывания анализатора (Issues для Юры).
FALSE_POSITIVES = {
    "s3_01_excellent.py": "DEEP_NESTING: цепочка if/elif считается вложенностью",
    "s3_02_good.py": "DEEP_NESTING: цепочка if/elif считается вложенностью",
    "s2_01_excellent.py": "NO_INPUT_VALIDATION на приватной функции _luhn с уже проверенным входом",
    "s2_02_good.py": "NO_INPUT_VALIDATION: isdigit()/len() без raise не считаются проверкой",
}


def found(row: dict) -> set[tuple[str, str]]:
    code = (SOLUTIONS / row["solution"]).read_text(encoding="utf-8")
    return {(item["code"], item["severity"]) for item in analyze(code)}


def expected(row: dict) -> set[tuple[str, str]]:
    return {tuple(item.split(":")) for item in filter(None, row["expected_findings"].split(";"))}


@pytest.mark.parametrize("row", ROWS, ids=[r["solution"] for r in ROWS])
def test_expected_findings_are_found(row):
    missing = expected(row) - found(row)
    assert not missing, f"анализатор не нашёл: {sorted(missing)}"


def _precision_params():
    for row in ROWS:
        reason = FALSE_POSITIVES.get(row["solution"])
        marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
        yield pytest.param(row, id=row["solution"], marks=marks)


@pytest.mark.parametrize("row", list(_precision_params()))
def test_no_unexpected_findings(row):
    extra = {code for code, _ in found(row)} - {code for code, _ in expected(row)}
    assert not extra, f"лишние замечания: {sorted(extra)}"
