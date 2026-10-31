"""Безопасный запуск кода кандидата в отдельном Docker-контейнере.

Ограничения: без сети, 5 секунд, 128 МБ памяти, не от root, корневая файловая система
только для чтения. Код кандидата никогда не выполняется в процессе backend.
Если Docker недоступен, код не запускается вовсе (статус "unavailable").

Проверки задачи: список вызовов, у каждого поле call (выражение) и expected (ожидаемый repr).
В контейнер передаются только вызовы (без ожидаемых значений): он печатает repr результатов,
а сравнивает их с эталоном backend. Поэтому код кандидата не может «напечатать успех»,
не зная правильных ответов, и объект с подменённым __eq__ тоже не пройдёт проверку.
"""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import TypedDict

DEFAULT_IMAGE = "python:3.12-slim"
OUTPUT_LIMIT = 2000
HOST_GRACE_SEC = 10
EXIT_TIMEOUT = 124
EXIT_OOM = 137
RESULTS_PREFIX = "__RESULTS__"

RUNNER = """\
import importlib.util
import json
from decimal import Decimal

spec = importlib.util.spec_from_file_location("solution", "/work/solution.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
namespace = dict(vars(module))
namespace.setdefault("Decimal", Decimal)

with open("/work/cases.json", encoding="utf-8") as handle:
    calls = json.load(handle)

results = []
for call in calls:
    try:
        results.append(repr(eval(call, namespace)))
    except BaseException as exc:
        results.append(type(exc).__name__)
print("__RESULTS__" + json.dumps(results))
"""


class RunResult(TypedDict):
    """Итог прогона: passed (прошло), failed (упало), timeout (превысило лимит), unavailable."""

    status: str
    output: str


def _limits() -> tuple[int, int]:
    timeout = int(os.getenv("SANDBOX_TIMEOUT_SEC", "5"))
    memory = int(os.getenv("SANDBOX_MEMORY_MB", "128"))
    return timeout, memory


def _docker_command(name: str, workdir: Path, timeout: int, memory_mb: int) -> list[str]:
    inner = (
        f"timeout {timeout} python -I /work/runner.py >/tmp/out 2>&1; code=$?; "
        f"head -c {OUTPUT_LIMIT} /tmp/out; exit $code"
    )
    return [
        "docker", "run", "--rm", "--name", name,
        "--network", "none",
        "--memory", f"{memory_mb}m", "--memory-swap", f"{memory_mb}m",
        "--cpus", "1", "--pids-limit", "64",
        "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-v", f"{workdir}:/work:ro",
        os.getenv("SANDBOX_IMAGE", DEFAULT_IMAGE),
        "sh", "-c", inner,
    ]  # fmt: skip


def parse_cases(tests: str) -> list[dict[str, str]]:
    """Разобрать проверки задачи; ошибка в формате означает ошибку сценария, а не кандидата."""
    cases = json.loads(tests)
    if not isinstance(cases, list) or not all(
        isinstance(item, dict) and {"call", "expected"} <= item.keys() for item in cases
    ):
        raise ValueError("tests должен быть списком объектов с полями call и expected")
    return cases


def _compare(output: str, cases: list[dict[str, str]]) -> RunResult:
    lines = [line for line in output.splitlines() if line.startswith(RESULTS_PREFIX)]
    if not lines:
        return {"status": "failed", "output": output.strip()[:OUTPUT_LIMIT] or "Нет результата."}
    try:
        results = json.loads(lines[-1][len(RESULTS_PREFIX) :])
    except json.JSONDecodeError:
        return {"status": "failed", "output": "Результат запуска не разобран."}
    if not isinstance(results, list) or len(results) != len(cases):
        return {"status": "failed", "output": "Результат запуска не совпал по длине."}
    wrong = [
        case["call"] for case, got in zip(cases, results, strict=True) if got != case["expected"]
    ]
    if wrong:
        return {
            "status": "failed",
            "output": f"Не прошло проверок: {len(wrong)} из {len(cases)}, например {wrong[0]}.",
        }
    return {"status": "passed", "output": f"Пройдено проверок: {len(cases)}."}


def run_tests(code: str, tests: str) -> RunResult:
    """Выполнить код кандидата на проверках задачи в контейнере и вернуть итог."""
    if shutil.which("docker") is None:
        return {"status": "unavailable", "output": "Docker недоступен: код не запускался."}
    cases = parse_cases(tests)

    timeout, memory_mb = _limits()
    name = f"sandbox-{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        (workdir / "solution.py").write_text(code, encoding="utf-8")
        (workdir / "runner.py").write_text(RUNNER, encoding="utf-8")
        (workdir / "cases.json").write_text(
            json.dumps([case["call"] for case in cases]), encoding="utf-8"
        )
        workdir.chmod(0o755)
        for item in workdir.iterdir():
            item.chmod(0o644)
        try:
            proc = subprocess.run(
                _docker_command(name, workdir, timeout, memory_mb),
                capture_output=True,
                text=True,
                timeout=timeout + HOST_GRACE_SEC,
            )
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True, check=False)
            return {"status": "timeout", "output": f"Превышен лимит времени {timeout} с."}

    if proc.returncode == EXIT_TIMEOUT:
        return {"status": "timeout", "output": f"Превышен лимит времени {timeout} с."}
    if proc.returncode == EXIT_OOM:
        return {"status": "failed", "output": f"Превышен лимит памяти {memory_mb} МБ."}
    if proc.returncode != 0:
        return {
            "status": "failed",
            "output": proc.stdout.strip()[:OUTPUT_LIMIT] or "Ошибка запуска.",
        }
    return _compare(proc.stdout, cases)
