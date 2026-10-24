"""Тесты заглушки модели и фабрики get_llm_client()."""

import json
import socket

import pytest

from app.llm import LLMClient, LLMConfigError, get_llm_client
from app.llm.stub import DEFAULT_JSON, DEFAULT_TEXT, StubClient


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Заглушка не должна открывать сетевые соединения."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("StubClient обратился к сети")

    monkeypatch.setattr(socket, "socket", _forbidden)


def test_stub_returns_text_without_json_hint():
    assert StubClient().complete("Ты ревьюер.", "код") == DEFAULT_TEXT


def test_stub_returns_valid_json_when_system_mentions_json():
    answer = StubClient().complete("Ответь строго в формате JSON.", "код")
    data = json.loads(answer)
    assert set(data["criteria"]) == {"correctness", "code_quality", "safety", "explanation"}
    assert data["feedback"]


def test_stub_custom_answers():
    client = StubClient(text="тест", json_answer='{"a": 1}')
    assert client.complete("обычный промпт", "x") == "тест"
    assert client.complete("верни JSON", "x") == '{"a": 1}'


def test_stub_records_calls():
    client = StubClient()
    client.complete("s", "u", temperature=0.2, max_tokens=100)
    assert client.calls == [{"system": "s", "user": "u", "temperature": 0.2, "max_tokens": 100}]


def test_stub_matches_protocol():
    assert isinstance(StubClient(), LLMClient)


def test_factory_uses_stub_by_default(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(get_llm_client(), StubClient)


def test_factory_stub_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", " STUB ")
    client = get_llm_client()
    assert isinstance(client, StubClient)
    assert client.complete("JSON", "x") == DEFAULT_JSON


def test_factory_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown-model")
    with pytest.raises(LLMConfigError) as exc:
        get_llm_client()
    assert "LLM_PROVIDER" in str(exc.value)
