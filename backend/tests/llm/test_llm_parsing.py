"""Тесты разбора JSON-ответа модели и одного повтора."""

import json

import pytest

from app.llm import LLMResponseError
from app.llm.parsing import LLMAnswer, complete_json, parse_llm_answer
from app.llm.stub import StubClient

GOOD = {
    "criteria": {"correctness": 20, "code_quality": 15, "safety": 10, "explanation": 25},
    "feedback": "Хорошее решение.",
}


def dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)


class SequenceClient:
    """Отдаёт ответы по очереди и запоминает запросы."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.users = []

    def complete(self, system, user, *, temperature=0.0, max_tokens=800):
        self.users.append(user)
        return self.answers.pop(0)


def test_parse_valid_answer():
    answer = parse_llm_answer(dumps(GOOD))
    assert answer == LLMAnswer(criteria=GOOD["criteria"], feedback="Хорошее решение.")


def test_parse_json_in_markdown_fence_with_extra_text():
    raw = "Вот оценка:\n```json\n" + dumps(GOOD) + "\n```\nУдачи!"
    assert parse_llm_answer(raw).criteria["explanation"] == 25


def test_parse_json_with_text_around_without_fence():
    assert parse_llm_answer("Ответ: " + dumps(GOOD) + " Конец.").feedback == "Хорошее решение."


def test_scores_are_clamped_and_rounded():
    data = {
        "criteria": {"correctness": 30, "code_quality": -5, "safety": 12.6, "explanation": "7"},
        "feedback": "ok",
    }
    assert parse_llm_answer(dumps(data)).criteria == {
        "correctness": 25,
        "code_quality": 0,
        "safety": 13,
        "explanation": 7,
    }


def test_long_feedback_is_truncated():
    data = {**GOOD, "feedback": "я" * 5000}
    assert len(parse_llm_answer(dumps(data)).feedback) == 1200


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "просто текст без JSON",
        "{сломанный json",
        "[1, 2, 3]",
        dumps({"feedback": "нет criteria"}),
        dumps({"criteria": {"correctness": 1}, "feedback": "не хватает ключей"}),
        dumps({"criteria": GOOD["criteria"], "feedback": "   "}),
        dumps({"criteria": GOOD["criteria"]}),
        dumps({"criteria": {**GOOD["criteria"], "safety": "много"}, "feedback": "x"}),
        dumps({"criteria": {**GOOD["criteria"], "safety": True}, "feedback": "x"}),
        dumps({"criteria": {**GOOD["criteria"], "safety": None}, "feedback": "x"}),
    ],
)
def test_parse_rejects_bad_format(raw):
    with pytest.raises(LLMResponseError):
        parse_llm_answer(raw)


def test_complete_json_no_retry_when_answer_is_good():
    client = SequenceClient(dumps(GOOD))
    assert complete_json(client, "JSON", "код").feedback == "Хорошее решение."
    assert len(client.users) == 1


def test_complete_json_retries_once_with_hint():
    client = SequenceClient("не json", dumps(GOOD))
    assert complete_json(client, "JSON", "код").criteria["correctness"] == 20
    assert len(client.users) == 2
    assert client.users[1].startswith("код")
    assert "не соответствует формату" in client.users[1]


def test_complete_json_gives_up_after_one_retry():
    client = SequenceClient("раз", "два", dumps(GOOD))
    with pytest.raises(LLMResponseError) as exc:
        complete_json(client, "JSON", "код")
    assert len(client.users) == 2
    assert "дважды" in str(exc.value)


def test_complete_json_passes_generation_params():
    client = StubClient()
    complete_json(client, "Ответь в формате JSON", "код", temperature=0.0, max_tokens=500)
    assert client.calls[0]["temperature"] == 0.0
    assert client.calls[0]["max_tokens"] == 500


def test_stub_json_answer_is_valid():
    assert complete_json(StubClient(), "Ответь в формате JSON", "код").feedback
