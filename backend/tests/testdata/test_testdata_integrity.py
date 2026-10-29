"""Целостность тестовых данных: файлы на месте, баллы и замечания в допустимых значениях."""

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3] / "testdata"
SOLUTIONS = ROOT / "solutions"
ROWS = list(csv.DictReader((SOLUTIONS / "expected.csv").open(encoding="utf-8")))
CRITERIA = ("correctness", "code_quality", "safety", "explanation")

# Коды, которые выдаёт анализатор (backend/app/analysis/rules). Только они в expected_findings.
ANALYZER_CODES = {
    "FLOAT_MONEY",
    "BARE_EXCEPT",
    "EVAL_EXEC",
    "NO_INPUT_VALIDATION",
    "LONG_FUNCTION",
    "UNUSED_VARIABLE",
    "DEEP_NESTING",
    "MISSING_RETURN",
}
SEVERITIES = {"low", "medium", "high"}


def parse(items: str) -> list[tuple[str, str]]:
    return [tuple(item.split(":")) for item in filter(None, items.split(";"))]


def test_solutions_count_in_range():
    assert 10 <= len(ROWS) <= 25
    assert {row["scenario"] for row in ROWS} == {"s1", "s2", "s3"}


def test_scores_spread_from_bad_to_good():
    totals = [int(row["expected_total"]) for row in ROWS]
    assert min(totals) < 20 and max(totals) > 90


def test_every_analyzer_rule_has_a_solution():
    covered = {code for row in ROWS for code, _ in parse(row["expected_findings"])}
    assert covered == ANALYZER_CODES


@pytest.mark.parametrize("row", ROWS, ids=[r["solution"] for r in ROWS])
def test_row_is_consistent(row):
    assert (SOLUTIONS / row["solution"]).is_file()
    assert row["solution"].startswith(row["scenario"] + "_")
    scores = [int(row[name]) for name in CRITERIA]
    assert all(0 <= score <= 25 for score in scores)
    assert sum(scores) == int(row["expected_total"])
    for code, severity in parse(row["expected_findings"]):
        assert code in ANALYZER_CODES, f"{code}: анализатор такой код не выдаёт"
        assert severity in SEVERITIES
    for code, severity in parse(row["expected_notes"]):
        assert code not in ANALYZER_CODES and code.islower(), f"{code}: место в expected_findings"
        assert severity in SEVERITIES


@pytest.mark.parametrize("row", ROWS, ids=[r["solution"] for r in ROWS])
def test_meta_matches_eval_format(row):
    """Метаданные в формате load_samples() из app/scoring/evaluation.py."""
    meta = json.loads((SOLUTIONS / row["meta"]).read_text(encoding="utf-8"))
    assert Path(row["meta"]).stem == Path(row["solution"]).stem
    assert meta["expected"] == int(row["expected_total"])
    assert meta["task"]
    assert 2 <= len(meta["questions"]) <= 3
    assert len(meta["answers"]) == len(meta["questions"])
    assert "findings" not in meta, "замечания должен находить анализатор, а не файл"


@pytest.mark.parametrize("path", sorted(SOLUTIONS.glob("*.py")), ids=lambda p: p.name)
def test_every_solution_is_listed_and_compiles(path):
    assert path.name in {row["solution"] for row in ROWS}
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_pii_dataset_is_complete():
    expected = json.loads((ROOT / "pii" / "expected.json").read_text(encoding="utf-8"))
    assert len(expected) == 10
    for name, spec in expected.items():
        text = (ROOT / "pii" / name).read_text(encoding="utf-8")
        for values in spec["pii"].values():
            assert all(value in text for value in values)
