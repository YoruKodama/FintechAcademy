"""Тесты безопасного запуска: ограничения контейнера и разбор результата.

Настоящий Docker нужен только интеграционным тестам; включаются SANDBOX_INTEGRATION=1.
"""

import os
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from app.analysis import run_tests, sandbox

CODE = "def add(a, b):\n    return a + b\n"
TESTS = "assert add(1, 2) == 3\n"


def fake_run(returncode=0, stdout="", capture=None):
    def runner(cmd, **kwargs):
        if capture is not None:
            capture.append((cmd, kwargs))
        marker = None
        if cmd[0] == "docker" and cmd[1] == "run":
            program = (next(p for p in _workdir(cmd).iterdir())).read_text(encoding="utf-8")
            marker = program.strip().splitlines()[-1][7:-2]
        out = stdout.replace("{marker}", marker or "")
        return SimpleNamespace(returncode=returncode, stdout=out, stderr="")

    return runner


def _workdir(cmd):
    from pathlib import Path

    mount = cmd[cmd.index("-v") + 1]
    return Path(mount.rsplit(":/work:ro", 1)[0])


@pytest.fixture(autouse=True)
def _docker_present(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: "/usr/bin/docker")


def test_unavailable_without_docker(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    result = run_tests(CODE, TESTS)
    assert result["status"] == "unavailable"


def test_container_limits_are_set(monkeypatch):
    calls = []
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, "{marker}\n", calls))
    run_tests(CODE, TESTS)
    cmd = calls[0][0]
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert cmd[cmd.index("--network") + 1] == "none"
    assert cmd[cmd.index("--memory") + 1] == "128m"
    assert cmd[cmd.index("--memory-swap") + 1] == "128m"
    assert cmd[cmd.index("--user") + 1] == "65534:65534"
    assert "--read-only" in cmd
    assert cmd[cmd.index("--cap-drop") + 1] == "ALL"
    assert "timeout 5 python" in cmd[-1]
    assert calls[0][1]["timeout"] > 5


def test_passed(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, "{marker}\n"))
    assert run_tests(CODE, TESTS)["status"] == "passed"


def test_exit_zero_without_marker_is_not_passed(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, "привет\n"))
    assert run_tests("import sys\nsys.exit(0)\n", TESTS)["status"] == "failed"


def test_failed(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(1, "AssertionError\n"))
    result = run_tests(CODE, TESTS)
    assert result["status"] == "failed"
    assert "AssertionError" in result["output"]


def test_timeout_exit_code(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(124))
    assert run_tests("while True:\n    pass\n", TESTS)["status"] == "timeout"


def test_memory_exit_code(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(137))
    result = run_tests("x = 'a' * 10**10\n", TESTS)
    assert result["status"] == "failed"
    assert "памяти" in result["output"]


def test_host_timeout_kills_container(monkeypatch):
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == "run":
            raise subprocess.TimeoutExpired(cmd, 15)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sandbox.subprocess, "run", runner)
    assert run_tests(CODE, TESTS)["status"] == "timeout"
    assert calls[-1][:2] == ["docker", "kill"]


def test_output_is_truncated(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(1, "x" * 10_000))
    assert len(run_tests(CODE, TESTS)["output"]) <= sandbox.OUTPUT_LIMIT


def test_limits_come_from_environment(monkeypatch):
    calls = []
    monkeypatch.setenv("SANDBOX_TIMEOUT_SEC", "3")
    monkeypatch.setenv("SANDBOX_MEMORY_MB", "64")
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, "{marker}", calls))
    run_tests(CODE, TESTS)
    cmd = calls[0][0]
    assert cmd[cmd.index("--memory") + 1] == "64m"
    assert "timeout 3 python" in cmd[-1]


needs_docker = pytest.mark.skipif(
    os.getenv("SANDBOX_INTEGRATION") != "1" or shutil.which("docker") is None,
    reason="нужен Docker и SANDBOX_INTEGRATION=1",
)


@needs_docker
def test_real_container_passes_and_fails(monkeypatch):
    monkeypatch.undo()
    assert run_tests(CODE, TESTS)["status"] == "passed"
    assert run_tests(CODE, "assert add(1, 2) == 4\n")["status"] == "failed"


@needs_docker
def test_real_container_stops_infinite_loop(monkeypatch):
    monkeypatch.undo()
    assert run_tests("while True:\n    pass\n", TESTS)["status"] == "timeout"


@needs_docker
def test_real_container_has_no_network(monkeypatch):
    monkeypatch.undo()
    code = (
        "import socket\n"
        "def add(a, b):\n"
        "    socket.create_connection(('example.com', 80), timeout=2)\n"
        "    return a + b\n"
    )
    assert run_tests(code, TESTS)["status"] == "failed"
