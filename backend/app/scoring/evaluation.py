"""Сравнение баллов системы с эталоном: загрузка решений, прогон и таблица для docs/eval.md.

Формат testdata/solutions/ (его нужно сверить с Андреем):
- `<имя>.py` — решение;
- `<имя>.json` (необязательно) — {"task": "...", "findings": [...], "questions": [...],
  "answers": [...], "expected": 78}; `expected` — эталонный балл 0..100.
Эталоны можно положить и в отдельный файл {"<имя>": 78, ...}.
"""

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.llm.base import LLMClient
from app.llm.types import Finding

from .pipeline import evaluate_solution

Analyzer = Callable[[str], Sequence[Finding]]


@dataclass
class Sample:
    name: str
    code: str
    findings: list[Finding] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    task: str | None = None
    expected: int | None = None
    has_findings: bool = False


@dataclass
class Row:
    name: str
    expected: int | None
    actual: int
    seconds: float

    @property
    def diff(self) -> int | None:
        return None if self.expected is None else self.actual - self.expected


def load_samples(solutions_dir: Path, expected_file: Path | None = None) -> list[Sample]:
    """Прочитать решения из папки. Порядок стабильный: по имени файла."""
    external = json.loads(expected_file.read_text(encoding="utf-8")) if expected_file else {}
    samples = []
    for code_path in sorted(solutions_dir.glob("*.py")):
        sample = Sample(name=code_path.stem, code=code_path.read_text(encoding="utf-8"))
        meta_path = code_path.with_suffix(".json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sample.task = meta.get("task")
            sample.questions = list(meta.get("questions", []))
            sample.answers = list(meta.get("answers", []))
            sample.expected = meta.get("expected")
            if "findings" in meta:
                sample.findings = list(meta["findings"])
                sample.has_findings = True
        if sample.name in external:
            sample.expected = external[sample.name]
        samples.append(sample)
    return samples


def run_eval(
    samples: Sequence[Sample],
    client: LLMClient,
    analyze: Analyzer | None = None,
    timer: Callable[[], float] = time.perf_counter,
) -> list[Row]:
    """Прогнать каждое решение через систему и записать балл и время."""
    rows = []
    for sample in samples:
        findings = sample.findings
        if not sample.has_findings and analyze is not None:
            findings = list(analyze(sample.code))
        started = timer()
        result = evaluate_solution(
            client, sample.code, findings, sample.questions, sample.answers, sample.task
        )
        rows.append(Row(sample.name, sample.expected, result["total"], timer() - started))
    return rows


def mean_abs_error(rows: Sequence[Row]) -> float | None:
    diffs = [abs(row.diff) for row in rows if row.diff is not None]
    return sum(diffs) / len(diffs) if diffs else None


def render_table(rows: Sequence[Row]) -> str:
    """Таблица в Markdown: решение, эталон, система, разница, время, плюс средние значения."""
    lines = [
        "| Решение | Эталон | Система | Разница | Время, с |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        expected = "—" if row.expected is None else str(row.expected)
        diff = "—" if row.diff is None else f"{row.diff:+d}"
        lines.append(f"| {row.name} | {expected} | {row.actual} | {diff} | {row.seconds:.1f} |")
    mae = mean_abs_error(rows)
    average_time = sum(row.seconds for row in rows) / len(rows) if rows else 0.0
    lines.append("")
    lines.append(f"Решений: {len(rows)}.")
    lines.append(
        "Средняя ошибка: "
        + ("нет эталонов для сравнения" if mae is None else f"{mae:.1f} балла")
        + "."
    )
    lines.append(f"Среднее время на решение: {average_time:.1f} с.")
    return "\n".join(lines)


def largest_gaps(rows: Sequence[Row], count: int = 3) -> list[Row]:
    """Решения с самой большой по модулю разницей — с них начинать разбор ошибок."""
    with_diff = [row for row in rows if row.diff is not None]
    return sorted(with_diff, key=lambda row: (-abs(row.diff), row.name))[:count]
