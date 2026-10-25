"""Целостность тестовых данных: файлы на месте, баллы и замечания в допустимых значениях."""

import csv
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3] / "testdata"
SOLUTIONS = ROOT / "solutions"
ROWS = list(csv.DictReader((SOLUTIONS / "expected.csv").open(encoding="utf-8")))
CATALOG = set(re.findall(r"^\| `(\w+)` \|", (ROOT / "README.md").read_text(encoding="utf-8"), re.M))
CRITERIA = ("correctness", "code_quality", "safety", "explanation")


def test_solutions_count_in_range():
    assert 10 <= len(ROWS) <= 20
    assert {row["scenario"] for row in ROWS} == {"s1", "s2", "s3"}


def test_scores_spread_from_bad_to_good():
    totals = [int(row["expected_total"]) for row in ROWS]
    assert min(totals) < 20 and max(totals) > 90


@pytest.mark.parametrize("row", ROWS, ids=[r["solution"] for r in ROWS])
def test_row_is_consistent(row):
    assert (SOLUTIONS / row["solution"]).is_file()
    answers = json.loads((SOLUTIONS / row["answers"]).read_text(encoding="utf-8"))
    assert answers["scenario"] == row["scenario"]
    assert 2 <= len(answers["answers"]) <= 3
    scores = [int(row[name]) for name in CRITERIA]
    assert all(0 <= score <= 25 for score in scores)
    assert sum(scores) == int(row["expected_total"])
    for item in filter(None, row["expected_findings"].split(";")):
        code, severity = item.split(":")
        assert code in CATALOG, f"код {code} не описан в testdata/README.md"
        assert severity in {"low", "medium", "high"}


@pytest.mark.parametrize("path", sorted(SOLUTIONS.glob("s*/*.py")), ids=lambda p: p.name)
def test_every_solution_is_listed_and_compiles(path):
    listed = {row["solution"] for row in ROWS}
    assert path.relative_to(SOLUTIONS).as_posix() in listed
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_pii_dataset_is_complete():
    expected = json.loads((ROOT / "pii" / "expected.json").read_text(encoding="utf-8"))
    assert len(expected) == 10
    for name, spec in expected.items():
        text = (ROOT / "pii" / name).read_text(encoding="utf-8")
        for values in spec["pii"].values():
            assert all(value in text for value in values)
