"""Точка входа backend: приложение FastAPI с методами из openapi.yaml."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine

from app.api import install_error_handlers, router
from app.db import init_db, make_engine, make_session_factory, seed_scenarios


def create_app(engine: Engine | None = None) -> FastAPI:
    """Собрать приложение; engine можно подменить в тестах."""
    engine = engine or make_engine()
    factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        with factory() as session:
            seed_scenarios(session)
        yield

    app = FastAPI(title="AI-тренажёр собеседований", version="0.1.0", lifespan=lifespan)
    app.state.session_factory = factory
    install_error_handlers(app)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Проверка, что сервис запущен."""
        return {"status": "ok"}

    return app


app = create_app()
