"""Тесты скрипта scripts/eval.py: запись таблицы в docs/eval.md и защита от заглушки."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

from app.scoring.evaluation import Row

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def eval_script():
    spec = importlib.util.spec_from_file_location("eval_script", ROOT / "scripts" / "eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_report_replaces_only_marked_block(eval_script, tmp_path):
    doc = tmp_path / "eval.md"
    doc.write_text(
        "# Заголовок\n\n<!-- eval:start -->\nстарое\n<!-- eval:end -->\n\nхвост\n",
        encoding="utf-8",
    )
    eval_script.write_report(doc, "НОВАЯ ТАБЛИЦА")
    assert doc.read_text(encoding="utf-8") == (
        "# Заголовок\n\n<!-- eval:start -->\nНОВАЯ ТАБЛИЦА\n<!-- eval:end -->\n\nхвост\n"
    )


def test_write_report_requires_markers(eval_script, tmp_path):
    doc = tmp_path / "eval.md"
    doc.write_text("без меток", encoding="utf-8")
    with pytest.raises(SystemExit):
        eval_script.write_report(doc, "x")


def test_real_doc_has_markers():
    text = (ROOT / "docs" / "eval.md").read_text(encoding="utf-8")
    assert "<!-- eval:start -->" in text and "<!-- eval:end -->" in text


def test_build_report_lists_largest_gaps(eval_script):
    rows = [Row("a", 80, 79, 1.0), Row("b", 60, 80, 1.0)]
    report = eval_script.build_report(rows)
    assert "| b | 60 | 80 | +20 | 1.0 |" in report
    assert "Больше всего расходятся: b (+20), a (-1)." in report


def test_stub_provider_does_not_touch_doc(eval_script, tmp_path, monkeypatch, capsys):
    solutions = tmp_path / "solutions"
    solutions.mkdir()
    (solutions / "one.py").write_text("print(1)\n", encoding="utf-8")
    doc = tmp_path / "eval.md"
    shutil.copy(ROOT / "docs" / "eval.md", doc)
    before = doc.read_text(encoding="utf-8")

    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setattr(sys, "argv", ["eval.py", "--solutions", str(solutions), "--doc", str(doc)])
    assert eval_script.main() == 0

    assert doc.read_text(encoding="utf-8") == before
    assert "docs/eval.md не изменён" in capsys.readouterr().out


def test_missing_solutions_folder(eval_script, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["eval.py", "--solutions", str(tmp_path / "nope")])
    assert eval_script.main() == 1
    assert "testdata/solutions" in capsys.readouterr().out
