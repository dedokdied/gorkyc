# Backend

FastAPI + PostgreSQL. Общий backend для Telegram MVP и будущего веба.
Владельцы: A — домен, данные и поиск; B — ассистент, интеграции LLM/STT/TTS.
Границы ownership — в [`../ROLES.md`](../ROLES.md).
Модели API-first — в
[`../docs/decisions/0003-api-first-models.md`](../docs/decisions/0003-api-first-models.md);
локальный резерв — в
[`../docs/decisions/0002-free-local-stack.md`](../docs/decisions/0002-free-local-stack.md).

## Слои

```
app/
├── main.py                  # создание приложения, роутеры, lifespan
├── api/                     # HTTP-слой, без бизнес-логики
│   ├── deps.py              # зависимости: сессия БД, текущий пользователь
│   ├── events.py            # A: CRUD, список, complete
│   ├── search.py            # A: поиск
│   ├── chat.py              # B: текст, история, уточнения
│   ├── voice.py             # B: аудио → STT → chat
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
│   ├── reminders.py         # A: выборка due-напоминаний
│   ├── dialogue.py          # B
│   ├── assistant.py         # B: оркестрация LLM + tools
│   └── assistant_tools.py   # B: ToolExecutor через A-сервисы
├── integrations/            # внешние сервисы
│   ├── llm.py               # B
│   ├── stt.py               # B
│   ├── tts.py               # B
│   ├── telegram_notifier.py # B: отправка напоминаний
│   └── embeddings.py        # A
└── workers/                 # фоновый worker напоминаний
```

## Правила

- В `api/` нет SQL и вызовов LLM напрямую: только валидация и вызов сервисов.
- В `services/` нет `Request`, `HTTPException` и знания о FastAPI.
- В `repositories/` нет бизнес-правил: только выборки и запись.
- Все даты — `timestamptz` (UTC), таймзона пользователя — в профиле.
- `user_id` берётся из auth-контекста, никогда из аргументов LLM.
- Все tool-аргументы проходят Pydantic-валидацию.
- Backend не импортирует aiogram: Telegram-бот общается с ним по HTTP.
- Напоминания: фоновый worker в backend раз в `REMINDERS_INTERVAL_SECONDS`
  выбирает due-события и отправляет их через `TelegramNotifier`.

## Клиенты

| Клиент | Как работает |
|---|---|
| Telegram-бот | `telegram_bot/` → `/chat`, `/voice` с `X-Telegram-Id` и `X-Bot-Secret` |
| Web (этап 2) | React → тот же API с `X-Demo-User: demo` |

Бот не дублирует бизнес-логику: только Telegram UI и вызовы API.

## Ассистент (этап 2, зона B)

- `schemas/chat.py` — DTO `/chat`, `action`, `clarification`.
- `schemas/tools.py` — аргументы tools.
- `integrations/llm.py` — API-first через OpenAI-compatible протокол,
  `FallbackLLM`, `RuleBasedLLM`; локальный Ollama — опция.
- `services/assistant.py` — цикл LLM → tools → ответ, уточнения.
- `services/dialogue.py` — pending actions; пока in-memory.
- `tests/test_chat.py` — создание, уточнение, список, fallback.

`ToolExecutor` — протокол-стык с A: `services/assistant_tools.py` реализует
его через `EventService`, `SearchService` и `DatetimeParser`; SQL остаётся
в repositories.

## Голос и напоминания (этап 3, зона B)

- `integrations/stt.py` — `OpenAIWhisperSTT` (API) и локальный `FasterWhisperSTT`.
- `integrations/tts.py` — протокол TTS и `NullTTS`; озвучка после MVP.
- `integrations/telegram_notifier.py` — отправка напоминаний в Telegram.
- `services/voice.py` — аудио → STT → `Assistant` → `VoiceResult`.
- `api/chat.py`, `api/voice.py` — фабрики роутеров; `app/main.py` подключает
  их с `resolve_telegram_user` и общим `Assistant`.
- Для multipart `/voice` нужны `fastapi` и `python-multipart`.
- API-first: задай `LLM_API_KEY` и `STT_API_KEY`, URL — в `.env`.
- Локальный fallback: `STT_PROVIDER=faster-whisper` (`pip install faster-whisper`)
  или `LLM_PROVIDER=ollama` (`ollama pull qwen2.5:3b`).

Пример подключения:

```python
from app.api.chat import build_chat_router
from app.api.voice import build_voice_router

app.include_router(build_chat_router(
    assistant=assistant,
    resolve_user=resolve_telegram_user,
))
app.include_router(build_voice_router(
    voice=voice_service,
    resolve_user=resolve_telegram_user,
))
```

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
- `user_id` берётся из auth-контекста: `X-Telegram-Id` + `X-Bot-Secret` для
  бота или `X-Demo-User` для web/demo; никогда из тела запроса.
- Ошибки API возвращаются в конверте `{"error": {"code", "message",
  "request_id"}}`; `request_id` также пишется в `X-Request-ID` и логи.

## Векторный поиск

В текущем окружении `pgvector` недоступен, поэтому работает FTS (`russian`) +
`pg_trgm`, а `events.embedding` хранится как `JSONB`-заглушка. Флаг
`ENABLE_VECTOR_SEARCH=false`. Подробности и план включения —
`project/docs/decisions/0004-vector-search-deferred.md`.

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
