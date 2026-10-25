"""Тесты OllamaClient: сеть заменена моками, настоящий сервис не нужен."""

import json
import urllib.error

import pytest

from app.llm import LLMError, LLMUnavailableError, get_llm_client
from app.llm.ollama import DEFAULT_MODEL, DEFAULT_URL, OllamaClient


class FakeResponse:
    def __init__(self, body: dict | bytes):
        self._raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def ok(text: str = "Разбор готов.") -> FakeResponse:
    return FakeResponse({"message": {"role": "assistant", "content": text}})


class FakeUrlopen:
    """Отдаёт заранее заданные ответы или бросает исключения по очереди."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []
        self.timeouts = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x/api/chat", code, "err", {}, None)


@pytest.fixture
def pauses():
    return []


def make_client(monkeypatch, pauses, *outcomes, **kwargs):
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr("urllib.request.urlopen", fake)
    return OllamaClient(sleep=pauses.append, **kwargs), fake


def test_success_returns_content_and_builds_request(monkeypatch, pauses):
    client, fake = make_client(monkeypatch, pauses, ok("Всё хорошо."), url="http://ollama:11434/")
    assert client.complete("Ты ревьюер.", "код", temperature=0.0, max_tokens=300) == "Всё хорошо."

    request = fake.requests[0]
    assert request.full_url == "http://ollama:11434/api/chat"
    body = json.loads(request.data)
    assert body["model"] == DEFAULT_MODEL
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0.0, "num_predict": 300}
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][0]["content"].startswith("Ты ревьюер.")
    assert "на русском" in body["messages"][0]["content"]
    assert body["messages"][1] == {"role": "user", "content": "код"}
    assert fake.timeouts == [60]


def test_url_and_model_from_env(monkeypatch, pauses):
    monkeypatch.setenv("OLLAMA_URL", "http://gpu-box:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    client, fake = make_client(monkeypatch, pauses, ok())
    client.complete("s", "u")
    assert fake.requests[0].full_url == "http://gpu-box:11434/api/chat"
    assert json.loads(fake.requests[0].data)["model"] == "test-model"


def test_defaults_without_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    client = OllamaClient()
    assert (client.url, client.model) == (DEFAULT_URL, DEFAULT_MODEL)


def test_retries_twice_then_succeeds(monkeypatch, pauses):
    client, fake = make_client(
        monkeypatch, pauses, urllib.error.URLError("refused"), http_error(503), ok("ответ")
    )
    assert client.complete("s", "u") == "ответ"
    assert len(fake.requests) == 3
    assert pauses == [1.0, 2.0]


def test_gives_up_after_two_retries(monkeypatch, pauses):
    err = urllib.error.URLError("refused")
    client, fake = make_client(monkeypatch, pauses, err, err, err)
    with pytest.raises(LLMUnavailableError) as exc:
        client.complete("s", "u")
    assert len(fake.requests) == 3
    assert "Ollama" in str(exc.value) and "ollama pull" in str(exc.value)


def test_timeout_is_retried(monkeypatch, pauses):
    client, fake = make_client(monkeypatch, pauses, TimeoutError(), ok("ответ"))
    assert client.complete("s", "u") == "ответ"
    assert len(fake.requests) == 2


def test_broken_json_and_empty_content_are_retried(monkeypatch, pauses):
    client, fake = make_client(monkeypatch, pauses, FakeResponse(b"not json"), ok("  "), ok("да"))
    assert client.complete("s", "u") == "да"
    assert len(fake.requests) == 3


def test_missing_model_is_not_retried(monkeypatch, pauses):
    client, fake = make_client(monkeypatch, pauses, http_error(404))
    with pytest.raises(LLMError) as exc:
        client.complete("s", "u")
    assert len(fake.requests) == 1
    assert "ollama pull" in str(exc.value)
    assert not isinstance(exc.value, LLMUnavailableError)


def test_factory_returns_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert isinstance(get_llm_client(), OllamaClient)
