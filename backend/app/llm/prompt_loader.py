"""Загрузка текстов промптов из backend/app/llm/prompts/*.md."""

import re
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"
_CRITERIA_PLACEHOLDER = "{{CRITERIA}}"


@cache
def load_prompt(name: str) -> str:
    """Прочитать промпт по имени файла без расширения.

    Метка {{CRITERIA}} заменяется описанием критериев из criteria.md,
    поэтому критерии хранятся в одном месте для всех промптов.
    """
    if not re.fullmatch(r"[a-z_]+", name):
        raise ValueError(f"Недопустимое имя промпта: {name!r}")
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    criteria = (PROMPTS_DIR / "criteria.md").read_text(encoding="utf-8").strip()
    return text.replace(_CRITERIA_PLACEHOLDER, criteria).strip()
