# Голосовой ассистент для задач и встреч

Каркас проекта. Сначала делаем **Telegram MVP**, после приёмки — **веб-версию с
backend и frontend** на том же API.

- Полный план: [`../PLAN.md`](../PLAN.md)
- Роли и контракт: [`ROLES.md`](ROLES.md)
- API: [`docs/api/README.md`](docs/api/README.md)

## Фазы

1. **Telegram MVP** — текст, голос, 4 обязательных сценария, напоминания.
2. **Web** — React-интерфейс, чат, таймлайн, поиск, голос в браузере.
3. **Полировка** — тесты, CI, README, демо.

Веб не начинаем, пока Telegram MVP не проходит 4 сценария.

## Стек

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic.
- **БД:** PostgreSQL 16/17, FTS `russian`, `pg_trgm`, опционально `pgvector`.
- **LLM:** LiteLLM / OpenAI-compatible API с tool calling.
- **Telegram:** aiogram 3.x, long polling.
- **Голос:** faster-whisper локально или Whisper/Groq API; TTS — edge-tts.
- **Напоминания:** APScheduler + PostgreSQL job store.
- **Frontend (этап 2):** React + TypeScript + Vite, TanStack Query.
- **Инфраструктура:** Docker Compose, VPS/Fly.io/Render.

## Структура

```
project/
├── README.md
├── ROLES.md
├── .env.example
├── backend/
│   ├── README.md
│   ├── app/
│   │   ├── api/              # events, search, chat, voice, health
│   │   ├── core/             # конфиг, логирование
│   │   ├── models/           # SQLAlchemy
│   │   ├── schemas/          # Pydantic DTO и tool-схемы
│   │   ├── repositories/     # SQL
│   │   ├── services/         # домен, даты, поиск, диалог
│   │   ├── integrations/     # LLM, STT, TTS, Telegram notifier
│   │   └── workers/          # scheduler напоминаний
│   ├── migrations/
│   └── tests/
├── telegram_bot/
│   ├── README.md
│   ├── app/
│   │   ├── handlers/         # start, text, voice
│   │   ├── api_client.py     # HTTP-клиент к backend
│   │   ├── keyboards.py
│   │   └── config.py
│   └── tests/
├── frontend/                 # этап 2
├── infra/
│   ├── docker/               # api, postgres, bot, frontend
│   └── deploy/
├── docs/
│   ├── api/
│   └── decisions/
├── scripts/
└── data/
```

## Главное правило

**Сначала контракт — потом код.** В первый час фиксируем:

1. DTO и эндпоинты в `docs/api/README.md`.
2. Интерфейсы `EventService`, `SearchService`, `DatetimeParser`.
3. Формат `/chat`, `/voice` и `pending_actions`.
4. Маппинг Telegram `chat_id → user_id`.

После этого каждый работает в своих папках.

## Ветки

- `main` — стабильная ветка.
- `feat/core-*` — участник A.
- `feat/assistant-*` — участник B.
- Один PR — одна задача. Перед merge: тесты + self-review.
- Общие файлы (`docker-compose.yml`, `main.py`, `.env.example`) — отдельным PR
  или по договорённости.

## Ритм

- 10–15 минут утром: контракт и блокеры.
- 10 минут вечером: интеграция, 4 сценария, README.
- Любое изменение API — сначала сообщение, потом код.

## Критерий готовности каркаса

- Папки созданы, README описывает зоны.
- API-контракт зафиксирован.
- A может поднять БД и `/events` без бота.
- B может поднять бота на mock API без backend.
