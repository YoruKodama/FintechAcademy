# LLM-слой

Код лежит в `backend/app/llm/`. Весь остальной проект работает с моделью только через
интерфейс `LLMClient`, поэтому провайдер меняется переменной окружения, без правки кода.

## Интерфейс

```python
from app.llm import get_llm_client

client = get_llm_client()  # провайдер берётся из LLM_PROVIDER
answer = client.complete(system, user, temperature=0.0, max_tokens=800)
```

`complete` принимает системный и пользовательский текст и возвращает строку ответа.
Типы `Finding` и `Result` описаны в `app/llm/types.py`.

## Переменные окружения

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `LLM_PROVIDER` | `stub` | Выбор провайдера: `stub`, `ollama` (позже `gigachat`) |
| `OLLAMA_URL` | `http://localhost:11434` | Адрес сервиса Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Название модели в Ollama |

## Заглушка (`stub`)

`StubClient` не обращается к сети и возвращает заранее заданные ответы:

- если в системном промпте есть слово JSON, возвращается JSON с четырьмя критериями и разбором;
- иначе возвращается короткий текст.

Заглушка запоминает вызовы в `client.calls`, поэтому в тестах можно проверить, что именно
было отправлено модели. Для тестов достаточно `LLM_PROVIDER=stub` или `StubClient(...)` напрямую.

## Ollama (`ollama`)

`OllamaClient` ходит в `POST {OLLAMA_URL}/api/chat` с `stream: false`. Ко всем системным
промптам добавляется требование отвечать по-русски. Параметры запроса:

- таймаут 60 секунд;
- 2 повтора после первой неудачи (паузы 1 и 2 секунды) при отказе соединения, таймауте,
  ответе 5xx и пустом или сломанном ответе;
- модель не найдена (404) не повторяется, в ошибке сразу написана команда `ollama pull`.

Если модель недоступна, клиент бросает `LLMUnavailableError` с понятным текстом, а не падает
с трассировкой. Запросы идут только на `OLLAMA_URL`, во внешние сервисы ничего не отправляется.

Запуск локально:

```bash
ollama serve
ollama pull qwen2.5:7b-instruct
LLM_PROVIDER=ollama python -c "from app.llm import get_llm_client; print(get_llm_client().complete('Ты помощник.', 'Скажи привет.'))"
```

Предложение для `docker-compose.yml` (файл ведёт Юра, согласовать перед добавлением):

```yaml
  ollama:
    image: ollama/ollama
    volumes:
      - ollama-data:/root/.ollama
    ports:
      - "11434:11434"
# в backend: OLLAMA_URL=http://ollama:11434
# в volumes: ollama-data:
```

### Скорость ответа

Среднее время ответа на 5 тестовых решениях Андрея: **не замерено**. Замер делает
`scripts/eval.py` (колонка «время» в `docs/eval.md`) после появления `testdata/solutions/`.

## Ошибки

Все ошибки наследуются от `LLMError`, и их текст можно показывать пользователю:

- `LLMConfigError` — неверная настройка, например неизвестный `LLM_PROVIDER`;
- `LLMUnavailableError` — модель недоступна;
- `LLMResponseError` — ответ модели не соответствует формату.
