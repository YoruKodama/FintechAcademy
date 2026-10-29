"""Подключение к базе данных. Адрес берётся из переменной окружения DATABASE_URL."""

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


def make_engine(url: str | None = None) -> Engine:
    """Создать движок; для SQLite в памяти (тесты) соединение общее на весь процесс."""
    url = url or os.getenv("DATABASE_URL", "sqlite://")
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, pool_pre_ping=True)


def init_db(engine: Engine) -> None:
    """Создать таблицы, если их ещё нет."""
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Фабрика сессий для движка."""
    return sessionmaker(engine, expire_on_commit=False)
