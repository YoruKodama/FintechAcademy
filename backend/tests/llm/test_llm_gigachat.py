"""Тесты GigaChatClient на моках: настоящий сервис и ключ не нужны."""

import json
import ssl
import urllib.error

import pytest

from app.llm import LLMUnavailableError, get_llm_client
from app.llm.gigachat import AUTH_URL, CHAT_URL, GigaChatClient


class FakeResponse:
    def __init__(self, body: dict):
        self._raw = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def token(value: str = "tok-1", expires_at_ms: int = 2_000_000_000_000) -> FakeResponse:
    return FakeResponse({"access_token": value, "expires_at": expires_at_ms})


def answer(text: str = "Разбор готов.") -> FakeResponse:
    return FakeResponse({"choices": [{"message": {"role": "assistant", "content": text}}]})


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "err", {}, None)


class FakeUrlopen:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout=None, context=None):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_client(monkeypatch, *outcomes, **kwargs):
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr("urllib.request.urlopen", fake)
    kwargs.setdefault("credentials", "fake-credentials")
    kwargs.setdefault("clock", lambda: 1_000_000_000.0)
    return GigaChatClient(**kwargs), fake


def test_no_credentials_does_not_break_creation_but_fails_on_call(monkeypatch):
    monkeypatch.delenv("GIGACHAT_CREDENTIALS", raising=False)
    client = GigaChatClient()
    with pytest.raises(LLMUnavailableError) as exc:
        client.complete("s", "u")
    assert "GIGACHAT_CREDENTIALS" in str(exc.value)


def test_factory_works_without_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gigachat")
    monkeypatch.delenv("GIGACHAT_CREDENTIALS", raising=False)
    assert isinstance(get_llm_client(), GigaChatClient)


def test_success_gets_token_then_answer(monkeypatch):
    client, fake = make_client(monkeypatch, token(), answer("Всё хорошо."))
    assert client.complete("Ты ревьюер.", "код", temperature=0.0, max_tokens=300) == "Всё хорошо."

    auth, chat = fake.requests
    assert auth.full_url == AUTH_URL
    assert auth.get_header("Authorization") == "Basic fake-credentials"
    assert auth.get_header("Rquid")
    assert auth.data == b"scope=GIGACHAT_API_PERS"

    assert chat.full_url == CHAT_URL
    assert chat.get_header("Authorization") == "Bearer tok-1"
    body = json.loads(chat.data)
    assert body["model"] == "GigaChat"
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 300
    assert body["messages"][0]["content"].startswith("Ты ревьюер.")
    assert "на русском" in body["messages"][0]["content"]


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "from-env")
    monkeypatch.setenv("GIGACHAT_MODEL", "GigaChat-Pro")
    monkeypatch.setenv("GIGACHAT_SCOPE", "GIGACHAT_API_CORP")
    client, fake = make_client(monkeypatch, token(), answer(), credentials=None)
    client.complete("s", "u")
    assert fake.requests[0].get_header("Authorization") == "Basic from-env"
    assert fake.requests[0].data == b"scope=GIGACHAT_API_CORP"
    assert json.loads(fake.requests[1].data)["model"] == "GigaChat-Pro"


def test_token_is_cached_between_calls(monkeypatch):
    client, fake = make_client(monkeypatch, token(), answer("1"), answer("2"))
    assert client.complete("s", "u") == "1"
    assert client.complete("s", "u") == "2"
    assert [r.full_url for r in fake.requests] == [AUTH_URL, CHAT_URL, CHAT_URL]


def test_expired_token_is_refreshed(monkeypatch):
    now = [1_000_000_000.0]
    client, fake = make_client(
        monkeypatch,
        token("old", expires_at_ms=1_000_000_100_000),
        answer("1"),
        token("new"),
        answer("2"),
        clock=lambda: now[0],
    )
    client.complete("s", "u")
    now[0] += 200
    client.complete("s", "u")
    assert fake.requests[3].get_header("Authorization") == "Bearer new"


def test_401_refreshes_token_once(monkeypatch):
    client, fake = make_client(
        monkeypatch, token("old"), http_error(401), token("new"), answer("ок")
    )
    assert client.complete("s", "u") == "ок"
    assert fake.requests[3].get_header("Authorization") == "Bearer new"


def test_rejected_credentials(monkeypatch):
    client, _ = make_client(monkeypatch, http_error(401))
    with pytest.raises(LLMUnavailableError) as exc:
        client.complete("s", "u")
    assert "GIGACHAT_CREDENTIALS" in str(exc.value)


def test_rate_limit_message(monkeypatch):
    client, _ = make_client(monkeypatch, token(), http_error(429))
    with pytest.raises(LLMUnavailableError) as exc:
        client.complete("s", "u")
    assert "лимит" in str(exc.value)


def test_certificate_error_suggests_ca_bundle(monkeypatch):
    error = urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed"))
    client, _ = make_client(monkeypatch, error)
    with pytest.raises(LLMUnavailableError) as exc:
        client.complete("s", "u")
    assert "GIGACHAT_CA_BUNDLE" in str(exc.value)


def test_network_error_and_timeout(monkeypatch):
    client, _ = make_client(monkeypatch, urllib.error.URLError("refused"))
    with pytest.raises(LLMUnavailableError):
        client.complete("s", "u")
    client, _ = make_client(monkeypatch, TimeoutError())
    with pytest.raises(LLMUnavailableError):
        client.complete("s", "u")


@pytest.mark.parametrize(
    "bad", [{"choices": []}, {"x": 1}, {"choices": [{"message": {"content": " "}}]}]
)
def test_unexpected_answer_format(monkeypatch, bad):
    client, _ = make_client(monkeypatch, token(), FakeResponse(bad))
    with pytest.raises(LLMUnavailableError):
        client.complete("s", "u")
