"""Тесты цепочки submit: анализ кода, обезличивание, оценщик, запуск в песочнице."""

import pytest

from app.api import chain

CODE = "def f():\n    return 1\n"
VALIDATED = "def f(a):\n    if a < 0:\n        raise ValueError\n    return a\n"
FLOAT_CODE = "def f(a):\n    return a * 0.5\n"

MODEL_JSON = (
    '{"criteria": {"correctness": 20, "code_quality": 18, "safety": 22, "explanation": 15}, '
    '"feedback": "Разбор."}'
)


class RecordingClient:
    def __init__(self, answer=MODEL_JSON):
        self.answer = answer
        self.prompts = []

    def complete(self, system, user, **kwargs):
        self.prompts.append(user)
        return self.answer


@pytest.fixture(autouse=True)
def _stub_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "stub")


def test_chain_anonymizes_before_model(monkeypatch):
    client = RecordingClient()
    monkeypatch.setattr(chain, "get_llm_client", lambda: client)
    code = "# звоните +7 921 555-12-34\n" + CODE
    result = chain.run_chain(code, ["почта a.b@example.ru"], questions=["Почему?"])

    sent = "\n".join(client.prompts)
    assert "555-12-34" not in sent
    assert "a.b@example.ru" not in sent
    assert "Разбор." in result["feedback"]
    assert 0 <= result["total"] <= 100


def test_chain_passes_questions_and_task_to_model(monkeypatch):
    client = RecordingClient()
    monkeypatch.setattr(chain, "get_llm_client", lambda: client)
    chain.run_chain(CODE, ["ответ"], questions=["Почему float плох?"], task="Посчитать комиссию")

    sent = "\n".join(client.prompts)
    assert "Почему float плох?" in sent
    assert "Посчитать комиссию" in sent


def test_chain_model_error_does_not_fail(monkeypatch):
    class BrokenClient:
        def complete(self, system, user, **kwargs):
            raise chain.LLMError("нет связи")

    monkeypatch.setattr(chain, "get_llm_client", lambda: BrokenClient())
    result = chain.run_chain(CODE, ["ответ"], questions=["Вопрос"])
    assert "не удалось" in result["feedback"].lower()
    assert 0 <= result["total"] <= 100


def test_chain_broken_json_does_not_fail(monkeypatch):
    monkeypatch.setattr(chain, "get_llm_client", lambda: RecordingClient("это не JSON"))
    result = chain.run_chain(CODE, ["ответ"], questions=["Вопрос"])
    assert 0 <= result["total"] <= 100
    assert result["feedback"]


def test_chain_findings_reach_result_and_lower_safety(monkeypatch):
    monkeypatch.setattr(chain, "get_llm_client", lambda: RecordingClient())
    clean = chain.run_chain(VALIDATED, ["ок"])
    dirty = chain.run_chain(FLOAT_CODE, ["ок"])
    assert {item["code"] for item in dirty["findings"]} >= {"FLOAT_MONEY"}
    assert dirty["criteria"]["safety"] < clean["criteria"]["safety"]


def test_chain_works_with_stub_provider():
    result = chain.run_chain(CODE, ["ответ"], questions=["Вопрос"])
    assert set(result) == {"total", "criteria", "feedback", "findings"}


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
    found = chain.analyze_code(CODE, "assert f() == 1")
    assert [item["code"] for item in found] == expected


def test_sandbox_is_off_by_default(monkeypatch):
    import app.analysis as analysis

    monkeypatch.delenv("SANDBOX_ENABLED", raising=False)

    def boom(code, tests):
        raise AssertionError("песочница не должна запускаться")

    monkeypatch.setattr(analysis, "run_tests", boom)
    assert chain.analyze_code(CODE, "assert f() == 1") == []
