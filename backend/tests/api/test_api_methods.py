"""Тесты методов API: сценарии, прохождения, результат, список для руководителя."""

import pytest
from fastapi.testclient import TestClient

from app.db import make_engine
from app.main import create_app

CODE = "def calc_fee(amount):\n    return amount\n"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    with TestClient(create_app(make_engine("sqlite://"))) as test_client:
        yield test_client


def _answers(client, scenario_id=1):
    questions = client.get(f"/scenarios/{scenario_id}").json()["questions"]
    return [f"Ответ {i}" for i in range(len(questions))]


def _start(client, scenario_id=1):
    response = client.post("/attempts", json={"scenario_id": scenario_id})
    assert response.status_code == 201
    return response.json()


def _error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_scenarios_has_three(client):
    response = client.get("/scenarios")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert all(set(item) == {"id", "title"} for item in items)


def test_get_scenario(client):
    response = client.get("/scenarios/1")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "title", "description", "code_template", "questions"}
    assert 2 <= len(body["questions"]) <= 3


def test_get_scenario_not_found(client):
    _error(client.get("/scenarios/999"), 404, "scenario_not_found")


def test_start_attempt(client):
    attempt = _start(client)
    assert attempt["status"] == "started"
    assert attempt["scenario_id"] == 1
    assert attempt["result"] is None
    assert attempt["finished_at"] is None


def test_start_attempt_unknown_scenario(client):
    _error(client.post("/attempts", json={"scenario_id": 999}), 404, "scenario_not_found")


def test_start_attempt_bad_body(client):
    _error(client.post("/attempts", json={}), 422, "validation_error")


def test_submit_returns_result(client):
    attempt = _start(client)
    response = client.post(
        f"/attempts/{attempt['id']}/submit", json={"code": CODE, "answers": _answers(client)}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["finished_at"] is not None
    result = body["result"]
    assert 0 <= result["total"] <= 100
    assert set(result["criteria"]) == {"correctness", "code_quality", "safety", "explanation"}
    assert all(0 <= value <= 25 for value in result["criteria"].values())
    assert result["feedback"]
    assert [item["code"] for item in result["findings"]] == ["NO_INPUT_VALIDATION"]


def test_submit_empty_code(client):
    attempt = _start(client)
    response = client.post(
        f"/attempts/{attempt['id']}/submit", json={"code": "   ", "answers": _answers(client)}
    )
    _error(response, 422, "empty_code")


def test_submit_wrong_answers_count(client):
    attempt = _start(client)
    response = client.post(f"/attempts/{attempt['id']}/submit", json={"code": CODE, "answers": []})
    _error(response, 422, "wrong_answers_count")


def test_submit_twice_conflict(client):
    attempt = _start(client)
    payload = {"code": CODE, "answers": _answers(client)}
    assert client.post(f"/attempts/{attempt['id']}/submit", json=payload).status_code == 200
    _error(client.post(f"/attempts/{attempt['id']}/submit", json=payload), 409, "already_submitted")


def test_submit_unknown_attempt(client):
    response = client.post("/attempts/999/submit", json={"code": CODE, "answers": ["a", "b"]})
    _error(response, 404, "attempt_not_found")


def test_get_attempt_before_and_after_submit(client):
    attempt = _start(client)
    before = client.get(f"/attempts/{attempt['id']}").json()
    assert before["status"] == "started"
    assert before["result"] is None

    submitted = client.post(
        f"/attempts/{attempt['id']}/submit", json={"code": CODE, "answers": _answers(client)}
    ).json()
    after = client.get(f"/attempts/{attempt['id']}").json()
    assert after["status"] == "done"
    assert after["result"] == submitted["result"]


def test_get_attempt_not_found(client):
    _error(client.get("/attempts/999"), 404, "attempt_not_found")


def test_list_attempts_and_filter(client):
    first = _start(client, 1)
    _start(client, 2)
    client.post(
        f"/attempts/{first['id']}/submit", json={"code": CODE, "answers": _answers(client, 1)}
    )

    everything = client.get("/attempts").json()
    assert len(everything) == 2
    done = next(row for row in everything if row["id"] == first["id"])
    assert done["status"] == "done"
    assert done["total"] is not None
    assert done["scenario_title"]
    started = next(row for row in everything if row["id"] != first["id"])
    assert started["total"] is None

    only_second = client.get("/attempts", params={"scenario_id": 2}).json()
    assert [row["scenario_id"] for row in only_second] == [2]


def test_unknown_route_uses_error_format(client):
    _error(client.get("/nope"), 404, "not_found")


def test_dates_have_timezone(client):
    attempt = _start(client)
    client.post(
        f"/attempts/{attempt['id']}/submit", json={"code": CODE, "answers": _answers(client)}
    )
    row = client.get("/attempts").json()[0]
    full = client.get(f"/attempts/{attempt['id']}").json()
    assert row["started_at"].endswith("Z")
    assert full["started_at"].endswith("Z")
    assert full["finished_at"].endswith("Z")
