"""Проверки промптов: критерии подставлены, формат описан, персональных данных нет."""

import pytest

from app.llm.prompt_loader import PROMPTS_DIR, load_prompt
from app.llm.types import CRITERIA
from app.privacy import anonymize

PROMPT_NAMES = ["review_code", "evaluate_answer"]


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_prompt_has_criteria_and_json_format(name):
    prompt = load_prompt(name)
    assert "{{" not in prompt
    assert "JSON" in prompt
    assert "по-русски" in prompt
    for key in CRITERIA:
        assert key in prompt


def test_each_criterion_describes_0_10_25():
    text = (PROMPTS_DIR / "criteria.md").read_text(encoding="utf-8")
    sections = text.split("### ")[1:]
    assert len(sections) == len(CRITERIA)
    for section in sections:
        for score in ("**0 баллов", "**10 баллов", "**25 баллов"):
            assert score in section


@pytest.mark.parametrize("name", [*PROMPT_NAMES, "criteria"])
def test_prompts_contain_no_personal_data(name):
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    cleaned, mapping = anonymize(text)
    assert mapping == {}, mapping
    assert cleaned == text


def test_load_prompt_rejects_bad_names():
    with pytest.raises(ValueError):
        load_prompt("../secrets")
