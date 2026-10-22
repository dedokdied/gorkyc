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
│   └── logging.py           # structlog, request_id
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

## Запуск (когда появится код)

```bash
cd project/backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Тесты:

```bash
pytest
ruff check .
mypy app
```
