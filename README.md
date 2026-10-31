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

Три сценария загружаются в базу при первом запуске. Данные базы хранятся в томе `db_data`.

### Модель

По умолчанию работает заглушка (`LLM_PROVIDER=stub`): разбор не настоящий, баллы считаются по правилам из замечаний. Чтобы включить локальную модель Ollama:

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct
# в .env: LLM_PROVIDER=ollama
docker compose up -d --build backend
```

Замена на российскую модель: `LLM_PROVIDER=gigachat` и ключ в `GIGACHAT_CREDENTIALS` (подробности в [docs/llm.md](docs/llm.md)). GigaChat работает в облаке, поэтому текст перед ним всегда обезличивается; для режима «всё локально» используйте Ollama.

### Запуск кода кандидата

Код кандидата выполняется только в отдельном Docker-контейнере: без сети, 5 секунд, 128 МБ, не от root, файловая система только для чтения. Включается переменной `SANDBOX_ENABLED=1` и требует Docker на хосте backend.

**В `docker compose` из этого репозитория запуск выключен** (`SANDBOX_ENABLED=0`): в образе backend нет Docker, а давать контейнеру доступ к сокету Docker мы не стали из соображений безопасности. Анализ кода по 8 правилам (через `ast`, без выполнения) работает всегда. Подробный разбор: [docs/qa/security.md](docs/qa/security.md).

## Проверки и тесты

```bash
cd backend
pip install -r requirements.txt
ruff check --config ../ruff.toml .
pytest
```

- Интеграционные тесты песочницы с настоящим Docker: `SANDBOX_INTEGRATION=1 pytest tests/analysis`.
- Сквозной тест в браузере (Playwright) запускается в CI после `docker compose up`, см. [tests/e2e](tests/e2e).
- Чек-лист ручной проверки: [docs/qa/checklist.md](docs/qa/checklist.md).

## Структура

| Путь | Что там |
|---|---|
| `backend/app/api` | методы API и формат ошибок (Юра) |
| `backend/app/analysis` | 8 правил анализа кода и безопасный запуск (Юра) |
| `backend/app/db` | работа с PostgreSQL и начальные сценарии (Юра) |
| `backend/app/llm`, `scoring`, `privacy` | модель, баллы, обезличивание (Ангелина) |
| `backend/tests`, `tests/e2e`, `testdata`, `.github` | тесты, данные и CI (Андрей) |
| `frontend/` | React + TypeScript + Vite + Monaco Editor (Юра) |
| `docs/jury` | материалы для жюри |
| `docs/qa` | отчёты тестирования и безопасность |

## Правила

Без реальных данных и секретов, секреты только из окружения. Изменения в `main` через PR с зелёным CI.
