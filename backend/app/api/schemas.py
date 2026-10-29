"""Схемы запросов и ответов API. Описание контракта: openapi.yaml."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScenarioShort(BaseModel):
    """Сценарий в списке."""

    id: int
    title: str


class Scenario(BaseModel):
    """Сценарий целиком: условие, шаблон кода и вопросы."""

    id: int
    title: str
    description: str
    code_template: str
    questions: list[str]


class AttemptStart(BaseModel):
    """Запрос на начало прохождения."""

    scenario_id: int


class Submission(BaseModel):
    """Решение кандидата и ответы на вопросы сценария."""

    code: str
    answers: list[str]


class Finding(BaseModel):
    """Замечание к коду."""

    code: str
    severity: Literal["low", "medium", "high"]
    line: int = Field(ge=1)
    message: str


class Criteria(BaseModel):
    """Четыре критерия оценки, каждый от 0 до 25."""

    correctness: int = Field(ge=0, le=25)
    code_quality: int = Field(ge=0, le=25)
    safety: int = Field(ge=0, le=25)
    explanation: int = Field(ge=0, le=25)


class Result(BaseModel):
    """Итог проверки решения."""

    total: int = Field(ge=0, le=100)
    criteria: Criteria
    feedback: str = Field(max_length=1200)
    findings: list[Finding]


class Attempt(BaseModel):
    """Прохождение; result заполнен, когда status = done."""

    id: int
    scenario_id: int
    status: Literal["started", "done"]
    started_at: datetime
    finished_at: datetime | None = None
    result: Result | None = None


class AttemptSummary(BaseModel):
    """Строка списка прохождений для руководителя."""

    id: int
    scenario_id: int
    scenario_title: str
    status: Literal["started", "done"]
    started_at: datetime
    total: int | None = Field(default=None, ge=0, le=100)
