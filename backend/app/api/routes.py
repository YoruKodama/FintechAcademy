"""Методы API из openapi.yaml."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Attempt, Scenario

from . import chain, schemas
from .errors import ApiError

router = APIRouter()


def get_session(request: Request) -> Iterator[Session]:
    """Одна сессия БД на запрос."""
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def _scenario_or_404(session: Session, scenario_id: int) -> Scenario:
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise ApiError(404, "scenario_not_found", "Сценарий не найден.")
    return scenario


def _attempt_or_404(session: Session, attempt_id: int) -> Attempt:
    attempt = session.get(Attempt, attempt_id)
    if attempt is None:
        raise ApiError(404, "attempt_not_found", "Прохождение не найдено.")
    return attempt


def _utc(value: datetime | None) -> datetime | None:
    """Привести время к UTC: SQLite отдаёт его без часового пояса."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _attempt_out(attempt: Attempt) -> schemas.Attempt:
    return schemas.Attempt(
        id=attempt.id,
        scenario_id=attempt.scenario_id,
        status=attempt.status,
        started_at=_utc(attempt.started_at),
        finished_at=_utc(attempt.finished_at),
        result=schemas.Result.model_validate(attempt.result) if attempt.result else None,
    )


@router.get("/scenarios", response_model=list[schemas.ScenarioShort])
def list_scenarios(session: SessionDep) -> list[schemas.ScenarioShort]:
    """Список сценариев."""
    rows = session.scalars(select(Scenario).order_by(Scenario.id)).all()
    return [schemas.ScenarioShort(id=row.id, title=row.title) for row in rows]


@router.get("/scenarios/{scenario_id}", response_model=schemas.Scenario)
def get_scenario(scenario_id: int, session: SessionDep) -> schemas.Scenario:
    """Сценарий целиком: условие, шаблон кода и вопросы."""
    row = _scenario_or_404(session, scenario_id)
    return schemas.Scenario(
        id=row.id,
        title=row.title,
        description=row.description,
        code_template=row.code_template,
        questions=row.questions,
    )


@router.post("/attempts", response_model=schemas.Attempt, status_code=201)
def start_attempt(body: schemas.AttemptStart, session: SessionDep) -> schemas.Attempt:
    """Начать прохождение сценария."""
    _scenario_or_404(session, body.scenario_id)
    attempt = Attempt(scenario_id=body.scenario_id, status="started")
    session.add(attempt)
    session.commit()
    return _attempt_out(attempt)


@router.get("/attempts", response_model=list[schemas.AttemptSummary])
def list_attempts(
    session: SessionDep, scenario_id: int | None = None
) -> list[schemas.AttemptSummary]:
    """Список прохождений для руководителя, с фильтром по сценарию."""
    query = select(Attempt).order_by(Attempt.id.desc())
    if scenario_id is not None:
        query = query.where(Attempt.scenario_id == scenario_id)
    return [
        schemas.AttemptSummary(
            id=row.id,
            scenario_id=row.scenario_id,
            scenario_title=row.scenario.title,
            status=row.status,
            started_at=_utc(row.started_at),
            total=row.result["total"] if row.result else None,
        )
        for row in session.scalars(query)
    ]


@router.get("/attempts/{attempt_id}", response_model=schemas.Attempt)
def get_attempt(attempt_id: int, session: SessionDep) -> schemas.Attempt:
    """Прохождение и результат."""
    return _attempt_out(_attempt_or_404(session, attempt_id))


@router.post("/attempts/{attempt_id}/submit", response_model=schemas.Attempt)
def submit_attempt(
    attempt_id: int, body: schemas.Submission, session: SessionDep
) -> schemas.Attempt:
    """Принять решение, пропустить через цепочку проверки и сохранить результат."""
    attempt = _attempt_or_404(session, attempt_id)
    if attempt.status == "done":
        raise ApiError(409, "already_submitted", "Решение по этому прохождению уже отправлено.")
    if not body.code.strip():
        raise ApiError(422, "empty_code", "Решение пустое: напишите код.")
    if len(body.answers) != len(attempt.scenario.questions):
        raise ApiError(
            422, "wrong_answers_count", "Число ответов не совпадает с числом вопросов сценария."
        )

    result = schemas.Result.model_validate(
        chain.run_chain(
            body.code,
            body.answers,
            attempt.scenario.tests,
            attempt.scenario.questions,
            attempt.scenario.description,
        )
    )
    attempt.code = body.code
    attempt.answers = body.answers
    attempt.result = result.model_dump()
    attempt.status = "done"
    attempt.finished_at = datetime.now(UTC)
    session.commit()
    return _attempt_out(attempt)
