"""Загрузка сценариев из seed/scenarios.json в пустую базу."""

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Scenario

SEED_FILE = Path(__file__).parent / "seed" / "scenarios.json"


def seed_scenarios(session: Session, path: Path = SEED_FILE) -> int:
    """Добавить сценарии, если таблица пуста. Вернуть число добавленных."""
    if session.scalar(select(func.count()).select_from(Scenario)):
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        session.add(
            Scenario(
                title=item["title"],
                description=item["description"],
                code_template=item["code_template"],
                questions=item["questions"],
                tests=item.get("tests"),
            )
        )
    session.commit()
    return len(items)
