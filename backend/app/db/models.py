"""Таблицы PostgreSQL: сценарии и прохождения (результат хранится в прохождении)."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Базовый класс таблиц."""


class Scenario(Base):
    """Сценарий: условие задачи, шаблон кода, вопросы и проверки для запуска кода."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    code_template: Mapped[str] = mapped_column(Text)
    questions: Mapped[list[str]] = mapped_column(JSON)
    tests: Mapped[str | None] = mapped_column(Text, nullable=True)


class Attempt(Base):
    """Прохождение сценария: состояние, присланное решение и готовый результат."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scenario: Mapped[Scenario] = relationship()
