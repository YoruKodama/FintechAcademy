"""Т6: прогон testdata/security/ через настоящую песочницу (Docker), без API и без pytest.

Нужно: Docker (Docker Desktop запущен) и Python 3.10+. Из корня репозитория:
    python tests/security/run_sandbox_suite.py

Каждый файл-атака запускается функцией run_tests() из backend/app/analysis/sandbox.py
на проверках сценария 1 («Расчёт комиссии за перевод»). Итог печатается и пишется
в docs/qa/security-sandbox-run.md — готовая таблица для docs/qa/security.md.
"""

import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.analysis.sandbox import run_tests  # noqa: E402

CASES = ROOT / "testdata" / "security"
SEED = ROOT / "backend" / "app" / "db" / "seed" / "scenarios.json"
OUT = ROOT / "docs" / "qa" / "security-sandbox-run.md"

# Что считаем «Ок» для каждой атаки: допустимые статусы run_tests.
EXPECTED = {
    "sec_01_infinite_loop": {"timeout"},
    "sec_02_memory_bomb": {"failed"},
    "sec_03_network": {"failed"},
    "sec_04_read_system_files": {"failed"},
    "sec_05_os_system": {"failed"},
    "sec_06_fork_bomb": {"failed", "timeout"},
    "sec_07_write_disk": {"failed"},
    "sec_08_subprocess_shell": {"failed"},
    "sec_09_huge_output": {"failed"},
    "sec_10_prompt_injection": {"failed"},
    "sec_11_import_tricks": {"failed"},
    "sec_12_long_literal": {"failed"},
    "sec_13_marker_bypass": {"failed"},
    "sec_14_eq_bypass": {"failed"},
}
CONTROL = {
    "s1_01_excellent (контроль)": (ROOT / "testdata/solutions/s1_01_excellent.py", {"passed"}),
    "s1_04_no_limits (контроль)": (ROOT / "testdata/solutions/s1_04_no_limits.py", {"failed"}),
}
LEAKS = ("POSTGRES", "DATABASE_URL", "change_me", "GIGACHAT", "YANDEX")


def main() -> int:
    if shutil.which("docker") is None:
        print("Docker не найден. Запустите Docker Desktop и повторите.")
        return 1
    docker = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if docker.returncode != 0:
        print("Docker установлен, но не запущен. Запустите Docker Desktop и повторите.")
        return 1
    print("Скачиваю образ python:3.12-slim (один раз)…")
    subprocess.run(["docker", "pull", "-q", "python:3.12-slim"], check=False)

    tests = json.dumps(json.loads(SEED.read_text(encoding="utf-8"))[0]["tests"])
    jobs = [(p.stem, p, EXPECTED.get(p.stem, {"failed"})) for p in sorted(CASES.glob("sec_*.py"))]
    jobs += [(name, path, ok) for name, (path, ok) in CONTROL.items()]

    rows = []
    for name, path, ok_statuses in jobs:
        started = time.perf_counter()
        result = run_tests(path.read_text(encoding="utf-8"), tests)
        seconds = time.perf_counter() - started
        output = " ".join(result["output"].split())[:160]
        leak = next((word for word in LEAKS if word in result["output"]), None)
        ok = result["status"] in ok_statuses and leak is None
        verdict = "✅" if ok else "❌"
        note = f"утечка: {leak}" if leak else output
        rows.append((name, result["status"], f"{seconds:.1f}", verdict, note))
        print(f"{verdict} {name:30} {result['status']:9} {seconds:5.1f} с  {note[:70]}")

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Прогон песочницы в Docker — {stamp}",
        "",
        f"Машина: {platform.system()} {platform.release()}, Python {platform.python_version()}. "
        "Проверки сценария 1. ✅ — статус ожидаемый и в выводе нет секретов/системных файлов.",
        "",
        "| Атака | Статус | Время, с | Ок? | Вывод |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {n} | {s} | {t} | {v} | {o.replace('|', '/')} |" for n, s, t, v, o in rows]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bad = sum(1 for row in rows if row[3] == "❌")
    print(f"\nГотово: {len(rows)} прогонов, проблем: {bad}. Таблица: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
