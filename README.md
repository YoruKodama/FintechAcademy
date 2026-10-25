# AI-тренажёр собеседований

Тренажёр для сотрудников банка: задача на Python, редактор кода, 2-3 вопроса, разбор от локальной модели и баллы 0-100.
Трек «Финтех без границ». Все данные в репозитории выдуманные.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

- Экран: http://localhost:3000
- API: http://localhost:8000 (проверка: `/health`)
- Описание API: [openapi.yaml](openapi.yaml), источник правды по контрактам

Модель по умолчанию в режиме заглушки (`LLM_MODE=stub`). Чтобы включить Ollama:

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct
# в .env: LLM_MODE=ollama
```

## Структура

| Путь | Что там |
|---|---|
| `backend/app/api` | методы API (Юра) |
| `backend/app/analysis` | анализ кода и безопасный запуск (Юра) |
| `backend/app/db` | работа с PostgreSQL (Юра) |
| `backend/app/llm`, `scoring`, `privacy` | модель, баллы, обезличивание (Ангелина) |
| `backend/tests`, `testdata`, `.github` | тесты и данные (Андрей) |
| `frontend/` | React + TypeScript + Vite + Monaco Editor |
| `docs/jury` | материалы для жюри |

## Правила

Один небольшой PR на задачу, без реальных данных и секретов, секреты только из окружения.
