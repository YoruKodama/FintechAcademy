"""Тесты цепочки submit: порядок шагов, обезличивание, подключение модулей Юры и Ангелины."""

import sys
import types

import pytest

from app.api import chain

CODE = "def f():\n    return 1\n"


@pytest.fixture(autouse=True)
def _stub_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "stub")


def test_chain_anonymizes_before_model(monkeypatch):
    seen = {}

    class FakeClient:
        def complete(self, system, user, **kwargs):
            seen["prompt"] = user
            return "Разбор."

    monkeypatch.setattr(chain, "get_llm_client", lambda: FakeClient())
    result = chain.run_chain("# звоните +7 921 555-12-34\n" + CODE, ["почта a.b@example.ru"])

    assert "555-12-34" not in seen["prompt"]
    assert "a.b@example.ru" not in seen["prompt"]
    assert "Разбор." in result["feedback"]


def test_chain_model_error_does_not_fail(monkeypatch):
    class BrokenClient:
        def complete(self, system, user, **kwargs):
            raise chain.LLMError("нет связи")

    monkeypatch.setattr(chain, "get_llm_client", lambda: BrokenClient())
    result = chain.run_chain(CODE, ["ответ"])
    assert "недоступна" in result["feedback"]
    assert 0 <= result["total"] <= 100


def test_chain_uses_analyzer_and_pipeline_when_present(monkeypatch):
    finding = {"code": "FLOAT_MONEY", "severity": "high", "line": 1, "message": "float для денег"}
    calls = []

    analysis = types.ModuleType("app.analysis")
    analysis.analyze = lambda code: calls.append("analyze") or [finding]
    analysis.run_tests = lambda code, tests: {"status": "passed", "output": ""}
    pipeline = types.ModuleType("app.pipeline")

    def run_pipeline(code, answers, findings):
        calls.append(("pipeline", findings))
        return {
            "total": 77,
            "criteria": {"correctness": 20, "code_quality": 19, "safety": 19, "explanation": 19},
            "feedback": "Готово.",
            "findings": findings,
        }

    pipeline.run_pipeline = run_pipeline
    monkeypatch.setitem(sys.modules, "app.analysis", analysis)
    monkeypatch.setitem(sys.modules, "app.pipeline", pipeline)

    result = chain.run_chain(CODE, ["ответ"])

    assert calls == ["analyze", ("pipeline", [finding])]
    assert result["total"] == 77
    assert result["findings"] == [finding]


def test_stub_total_drops_with_findings():
    findings = [
        {"code": "FLOAT_MONEY", "severity": "high", "line": 1, "message": "float"},
        {"code": "BARE_EXCEPT", "severity": "medium", "line": 2, "message": "except"},
    ]
    clean = chain._stub_pipeline(CODE, ["a"], [])
    dirty = chain._stub_pipeline(CODE, ["a"], findings)
    assert dirty["total"] < clean["total"]
    assert all(0 <= value <= 25 for value in dirty["criteria"].values())


def _fake_run(status):
    return lambda code, tests: {"status": status, "output": "AssertionError"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [("failed", ["TESTS_FAILED"]), ("timeout", ["TIMEOUT"]), ("passed", []), ("unavailable", [])],
)
def test_sandbox_result_becomes_findings(monkeypatch, status, expected):
    import app.analysis as analysis

    monkeypatch.setenv("SANDBOX_ENABLED", "1")
    monkeypatch.setattr(analysis, "run_tests", _fake_run(status))
    code = "def f():\n    return 1\n"
    found = chain.analyze_code(code, "assert f() == 1")
    assert [item["code"] for item in found] == expected


def test_sandbox_is_off_by_default(monkeypatch):
    import app.analysis as analysis

    monkeypatch.delenv("SANDBOX_ENABLED", raising=False)

    def boom(code, tests):
        raise AssertionError("песочница не должна запускаться")

    monkeypatch.setattr(analysis, "run_tests", boom)
    assert chain.analyze_code("def f():\n    return 1\n", "assert f() == 1") == []
