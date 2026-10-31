"""Тесты безопасного запуска: ограничения контейнера, сравнение результатов, обходы проверки.

Настоящий Docker нужен только интеграционным тестам; включаются SANDBOX_INTEGRATION=1.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.analysis import run_tests, sandbox

CODE = "def add(a, b):\n    return a + b\n"
CASES = [
    {"call": "add(1, 2)", "expected": "3"},
    {"call": "add('a', 'b')", "expected": "'ab'"},
]
TESTS = json.dumps(CASES)


def _workdir(cmd):
    mount = cmd[cmd.index("-v") + 1]
    return Path(mount.rsplit(":/work:ro", 1)[0])


def results_line(values):
    return sandbox.RESULTS_PREFIX + json.dumps(values)


def fake_run(returncode=0, stdout="", capture=None, files=None):
    def runner(cmd, **kwargs):
        if capture is not None:
            capture.append((cmd, kwargs))
        if files is not None and cmd[1] == "run":
            workdir = _workdir(cmd)
            for item in workdir.iterdir():
                files[item.name] = item.read_text(encoding="utf-8")
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    return runner


@pytest.fixture(autouse=True)
def _docker_present(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: "/usr/bin/docker")


def test_unavailable_without_docker(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    assert run_tests(CODE, TESTS)["status"] == "unavailable"


def test_container_limits_are_set(monkeypatch):
    calls = []
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, results_line(["3", "'ab'"]), calls))
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


def test_expected_values_never_reach_container(monkeypatch):
    files = {}
    monkeypatch.setattr(
        sandbox.subprocess, "run", fake_run(0, results_line(["3", "'ab'"]), files=files)
    )
    run_tests(CODE, TESTS)
    assert set(files) == {"solution.py", "runner.py", "cases.json"}
    assert json.loads(files["cases.json"]) == ["add(1, 2)", "add('a', 'b')"]
    assert "'ab'" not in files["runner.py"]
    assert files["solution.py"] == CODE


def test_passed(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, results_line(["3", "'ab'"])))
    result = run_tests(CODE, TESTS)
    assert result["status"] == "passed"


def test_noise_before_results_is_ignored(monkeypatch):
    out = "привет\n" + results_line(["3", "'ab'"]) + "\n"
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, out))
    assert run_tests(CODE, TESTS)["status"] == "passed"


def test_wrong_value_fails_without_leaking_expected(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, results_line(["3", "'xx'"])))
    result = run_tests(CODE, TESTS)
    assert result["status"] == "failed"
    assert "1 из 2" in result["output"]
    assert "add('a', 'b')" in result["output"]
    assert "'ab'" not in result["output"].replace("add('a', 'b')", "")


def test_exit_zero_without_results_is_not_passed(monkeypatch):
    """Код вызвал os._exit(0) или напечатал «успех»: результатов нет, значит, провал."""
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, "всё прошло, успех\n"))
    assert run_tests("import os\nos._exit(0)\n", TESTS)["status"] == "failed"


def test_results_of_wrong_length_fail(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, results_line(["3"])))
    assert run_tests(CODE, TESTS)["status"] == "failed"


def test_garbage_results_fail(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, sandbox.RESULTS_PREFIX + "{не json"))
    assert run_tests(CODE, TESTS)["status"] == "failed"


def test_nonzero_exit_is_failed(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(1, "Traceback: ошибка\n"))
    result = run_tests(CODE, TESTS)
    assert result["status"] == "failed"
    assert "Traceback" in result["output"]


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


def test_limits_come_from_environment(monkeypatch):
    calls = []
    monkeypatch.setenv("SANDBOX_TIMEOUT_SEC", "3")
    monkeypatch.setenv("SANDBOX_MEMORY_MB", "64")
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run(0, results_line(["3", "'ab'"]), calls))
    run_tests(CODE, TESTS)
    cmd = calls[0][0]
    assert cmd[cmd.index("--memory") + 1] == "64m"
    assert "timeout 3 python" in cmd[-1]


@pytest.mark.parametrize("bad", ["не json", "{}", '[{"call": "f()"}]', '["f()"]'])
def test_bad_tests_format_raises_value_error(bad):
    with pytest.raises(ValueError):
        run_tests(CODE, bad)


def test_seeded_scenarios_have_valid_tests():
    seed = Path(__file__).resolve().parents[2] / "app" / "db" / "seed" / "scenarios.json"
    for item in json.loads(seed.read_text(encoding="utf-8")):
        cases = sandbox.parse_cases(json.dumps(item["tests"]))
        assert len(cases) >= 5
        for case in cases:
            compile(case["call"], "<case>", "eval")


needs_docker = pytest.mark.skipif(
    os.getenv("SANDBOX_INTEGRATION") != "1" or shutil.which("docker") is None,
    reason="нужен Docker и SANDBOX_INTEGRATION=1",
)


@needs_docker
def test_real_container_passes_and_fails():
    assert run_tests(CODE, TESTS)["status"] == "passed"
    wrong = "def add(a, b):\n    return 0\n"
    assert run_tests(wrong, TESTS)["status"] == "failed"


@needs_docker
def test_real_container_stops_infinite_loop():
    assert run_tests("while True:\n    pass\n", TESTS)["status"] == "timeout"


@needs_docker
def test_real_container_has_no_network():
    code = (
        "import socket\n"
        "def add(a, b):\n"
        "    socket.create_connection(('example.com', 80), timeout=2)\n"
        "    return a + b\n"
    )
    assert run_tests(code, TESTS)["status"] == "failed"


@needs_docker
def test_real_container_rejects_early_exit():
    """os._exit(0) без результатов не считается успехом."""
    code = "import os\nos._exit(0)\n"
    assert run_tests(code, TESTS)["status"] == "failed"


@needs_docker
def test_real_container_rejects_eq_trick():
    code = (
        "class Anything:\n"
        "    def __eq__(self, other):\n        return True\n"
        "    def __repr__(self):\n        return 'Anything()'\n"
        "def add(a, b):\n    return Anything()\n"
    )
    assert run_tests(code, TESTS)["status"] == "failed"
