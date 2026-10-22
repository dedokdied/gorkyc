# Backend

FastAPI + PostgreSQL. Владельцы: A — домен, данные и поиск; B — ассистент,
интеграции LLM/STT/TTS. Общие файлы — по договорённости.

## Слои

```
app/
├── main.py                  # создание приложения, роутеры, lifespan
├── api/                     # HTTP-слой, без бизнес-логики
│   ├── deps.py              # зависимости: сессия БД, текущий пользователь
│   ├── events.py            # A: CRUD, список, complete
│   ├── search.py            # A: поиск
│   ├── chat.py              # B: текст, голос, история
│   └── health.py            # вместе
├── core/                    # конфиг, логи, безопасность
│   ├── config.py            # pydantic-settings, .env
│   ├── logging.py           # structlog, request_id
│   └── middleware.py        # X-Request-ID
├── models/                  # A: SQLAlchemy-модели
├── schemas/                 # DTO и tool-схемы
│   ├── events.py            # A
│   ├── search.py            # A
│   ├── chat.py              # B
│   └── tools.py             # B
├── repositories/            # A: запросы к БД
├── services/                # бизнес-логика
│   ├── events.py            # A
│   ├── datetime_parser.py   # A
│   ├── search.py            # A
│   ├── dialogue.py          # B
│   └── assistant.py         # B: оркестрация LLM + tools
├── integrations/            # внешние сервисы
│   ├── llm.py               # B
│   ├── stt.py               # B
│   ├── tts.py               # B
│   └── embeddings.py        # A
└── workers/                 # фоновые задачи, после ядра
```

## Правила

- В `api/` нет SQL и вызовов LLM напрямую: только валидация и вызов сервисов.
- В `services/` нет `Request`, `HTTPException` и знания о FastAPI.
- В `repositories/` нет бизнес-правил: только выборки и запись.
- Все даты — `timestamptz` (UTC), таймзона пользователя — в профиле.
- `user_id` берётся из auth-контекста, никогда из аргументов LLM.
- Все tool-аргументы проходят Pydantic-валидацию.

## Ключевые интерфейсы

```python
class EventService(Protocol):
    async def create(self, user_id, data: EventCreate) -> EventRead: ...
    async def update(self, user_id, event_id, data: EventPatch) -> EventRead: ...
    async def complete(self, user_id, event_id) -> EventRead: ...
    async def delete(self, user_id, event_id) -> None: ...
    async def list(self, user_id, period: Period, type: EventType | None) -> list[EventRead]: ...
    async def get(self, user_id, event_id) -> EventRead: ...

class SearchService(Protocol):
    async def search(self, user_id, query: str, filters: SearchFilters) -> list[SearchHit]: ...

class DatetimeParser(Protocol):
    def parse(self, expression: str, tz: str, now: datetime) -> ParsedTime: ...
```

## Контракт и разработка

- Сначала схемы в `docs/api/README.md`, затем Pydantic в `app/schemas/`.
- B может работать с mock-сервером, пока A не закончил БД.
- A может тестировать сервисы без LLM, пока B не подключил провайдера.
- Любое изменение DTO — через PR в `docs/api/README.md`.
- Схема БД управляется только Alembic. `Base.metadata.create_all` в runtime
  запрещён: он маскирует расхождения миграций.
- `user_id` берётся из `X-Demo-User` в текущем demo-режиме, не из тела запроса.
- Ошибки API возвращаются в конверте `{"error": {"code", "message",
  "request_id"}}`; `request_id` также пишется в `X-Request-ID` и логи.

## Векторный поиск

В текущем окружении `pgvector` недоступен, поэтому работает FTS (`russian`) +
`pg_trgm`, а `events.embedding` хранится как `JSONB`-заглушка. Флаг
`ENABLE_VECTOR_SEARCH=false`. Подробности и план включения —
`project/docs/decisions/0002-vector-search-deferred.md`.

## Запуск

```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/assistant"
alembic upgrade head
uvicorn app.main:app --reload
```

`alembic` читает `DATABASE_URL` из окружения (или `.env`) через
`app.core.config.settings`; URL в `alembic.ini` — только fallback.

## Тесты

Тесты используют отдельную БД `assistant_test` (создаётся автоматически) и не
трогают `assistant`. По умолчанию имя берётся из `DATABASE_URL` с суффиксом
`_test`; можно переопределить:

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/assistant_test"
pytest
ruff check .
mypy app
```

Проверка миграций на пустой БД:

```bash
createdb review_migrate
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/review_migrate" \
  alembic upgrade head
```

## Ограничения

- Векторный поиск отложен (см. ADR 0002).
- `sessions`/`messages` и `/chat` относятся к зоне B и в этом PR не меняются.
