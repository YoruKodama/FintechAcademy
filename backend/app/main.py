"""Точка входа backend. Методы API появятся в задаче Ю2."""
from fastapi import FastAPI

app = FastAPI(title="AI-тренажёр собеседований", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Проверка, что сервис запущен."""
    return {"status": "ok"}
