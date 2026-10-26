"""Прогон решений из testdata/solutions/ через систему и сравнение с эталоном.

Запуск из корня репозитория:
    LLM_PROVIDER=ollama python scripts/eval.py
Таблица записывается в docs/eval.md между метками <!-- eval:start --> и <!-- eval:end -->.
"""

import argparse
import importlib
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.llm import get_llm_client  # noqa: E402
from app.scoring.evaluation import (  # noqa: E402
    largest_gaps,
    load_samples,
    render_table,
    run_eval,
)

START, END = "<!-- eval:start -->", "<!-- eval:end -->"


def find_analyzer():
    """Анализатор кода лежит у Юры; если модуля пока нет, замечания берутся из файлов решений."""
    try:
        return importlib.import_module("app.analysis").analyze
    except (ImportError, AttributeError):
        return None


def build_report(rows) -> str:
    gaps = ", ".join(f"{row.name} ({row.diff:+d})" for row in largest_gaps(rows))
    lines = [render_table(rows)]
    if gaps:
        lines.append(f"Больше всего расходятся: {gaps}.")
    return "\n".join(lines)


def write_report(doc_path: Path, report: str) -> None:
    text = doc_path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"В {doc_path} нет меток {START} и {END}.")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    doc_path.write_text(f"{head}{START}\n{report}\n{END}{tail}", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--solutions", type=Path, default=ROOT / "testdata" / "solutions")
    parser.add_argument("--expected", type=Path, help="JSON {имя: эталонный балл}")
    parser.add_argument("--doc", type=Path, default=ROOT / "docs" / "eval.md")
    parser.add_argument("--no-write", action="store_true", help="только напечатать таблицу")
    parser.add_argument(
        "--allow-stub", action="store_true", help="разрешить запись при LLM_PROVIDER=stub"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    if not args.solutions.is_dir():
        print(f"Нет папки с решениями: {args.solutions}. Ждём testdata/solutions/ от Андрея.")
        return 1
    samples = load_samples(args.solutions, args.expected)
    if not samples:
        print(f"В {args.solutions} нет файлов *.py.")
        return 1

    provider = os.getenv("LLM_PROVIDER", "stub")
    report = build_report(run_eval(samples, get_llm_client(), find_analyzer()))
    print(report)

    if args.no_write:
        return 0
    if provider == "stub" and not args.allow_stub:
        print("\nLLM_PROVIDER=stub: баллы заглушки не отражают модель, docs/eval.md не изменён.")
        return 0
    write_report(args.doc, report)
    print(f"\nТаблица записана в {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
