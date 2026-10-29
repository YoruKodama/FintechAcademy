"""Безопасный запуск кода кандидата в отдельном Docker-контейнере.

Ограничения: без сети, 5 секунд, 128 МБ памяти, не от root, корневая файловая система
только для чтения. Код кандидата никогда не выполняется в процессе backend.
Если Docker недоступен, код не запускается вовсе (статус "unavailable").
"""

import os
import secrets
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
        f"timeout {timeout} python -I /work/main.py >/tmp/out 2>&1; code=$?; "
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


def run_tests(code: str, tests: str) -> RunResult:
    """Выполнить код кандидата вместе с проверками задачи в контейнере и вернуть итог."""
    if shutil.which("docker") is None:
        return {"status": "unavailable", "output": "Docker недоступен: код не запускался."}

    timeout, memory_mb = _limits()
    marker = f"__OK_{secrets.token_hex(8)}__"
    name = f"sandbox-{uuid.uuid4().hex[:12]}"
    program = f"{code}\n\n{tests}\nprint({marker!r})\n"

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        (workdir / "main.py").write_text(program, encoding="utf-8")
        workdir.chmod(0o755)
        (workdir / "main.py").chmod(0o644)
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

    output = proc.stdout.replace(marker, "").strip()[:OUTPUT_LIMIT]
    if proc.returncode == EXIT_TIMEOUT:
        return {"status": "timeout", "output": f"Превышен лимит времени {timeout} с."}
    if proc.returncode == EXIT_OOM:
        return {"status": "failed", "output": f"Превышен лимит памяти {memory_mb} МБ."}
    if proc.returncode == 0 and marker in proc.stdout:
        return {"status": "passed", "output": output}
    return {"status": "failed", "output": output or "Решение не прошло проверки."}
