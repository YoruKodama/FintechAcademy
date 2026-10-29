"""Тесты сравнения с эталоном: загрузка решений, прогон, таблица."""

import json

from app.llm.stub import StubClient
from app.scoring.evaluation import (
    Row,
    largest_gaps,
    load_samples,
    mean_abs_error,
    render_table,
    run_eval,
)


def make_solutions(tmp_path):
    (tmp_path / "b_second.py").write_text("print('второе')\n", encoding="utf-8")
    (tmp_path / "a_first.py").write_text("print('первое')\n", encoding="utf-8")
    meta = {
        "expected": 70,
        "questions": ["Почему Decimal?"],
        "answers": ["Потому что float теряет точность при расчётах с деньгами."],
        "findings": [{"code": "FLOAT_MONEY", "severity": "high", "line": 1, "message": "float"}],
    }
    (tmp_path / "a_first.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_load_samples_sorted_with_sidecar_and_external_expected(tmp_path):
    folder = make_solutions(tmp_path)
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({"b_second": 55}), encoding="utf-8")

    first, second = load_samples(folder, expected)
    assert (first.name, second.name) == ("a_first", "b_second")
    assert first.expected == 70 and first.has_findings and first.questions == ["Почему Decimal?"]
    assert second.expected == 55 and not second.has_findings


def test_run_eval_scores_every_solution_and_measures_time(tmp_path):
    samples = load_samples(make_solutions(tmp_path))
    ticks = iter([0.0, 2.0, 2.0, 5.5])
    rows = run_eval(samples, StubClient(), timer=lambda: next(ticks))
    assert [row.name for row in rows] == ["a_first", "b_second"]
    assert [row.seconds for row in rows] == [2.0, 3.5]
    assert all(0 <= row.actual <= 100 for row in rows)


def test_run_eval_uses_analyzer_only_when_findings_not_given(tmp_path):
    samples = load_samples(make_solutions(tmp_path))
    seen = []

    def analyze(code):
        seen.append(code)
        return []

    run_eval(samples, StubClient(), analyze)
    assert seen == ["print('второе')\n"]


def test_row_diff_and_mean_error():
    rows = [Row("a", 80, 74, 1.0), Row("b", 60, 70, 1.0), Row("c", None, 50, 1.0)]
    assert [row.diff for row in rows] == [-6, 10, None]
    assert mean_abs_error(rows) == 8.0
    assert mean_abs_error([Row("c", None, 50, 1.0)]) is None


def test_render_table():
    rows = [Row("a", 80, 74, 12.34), Row("b", 60, 70, 7.0), Row("c", None, 50, 1.0)]
    table = render_table(rows)
    assert "| Решение | Эталон | Система | Разница | Время, с |" in table
    assert "| a | 80 | 74 | -6 | 12.3 |" in table
    assert "| b | 60 | 70 | +10 | 7.0 |" in table
    assert "| c | — | 50 | — | 1.0 |" in table
    assert "Средняя ошибка: 8.0 балла." in table
    assert "Среднее время на решение: 6.8 с." in table


def test_render_table_without_expected_values():
    assert "нет эталонов для сравнения" in render_table([Row("a", None, 50, 1.0)])


def test_largest_gaps():
    rows = [Row("a", 80, 79, 1), Row("b", 60, 80, 1), Row("c", 50, 40, 1), Row("d", 50, 50, 1)]
    assert [row.name for row in largest_gaps(rows, 2)] == ["b", "c"]
