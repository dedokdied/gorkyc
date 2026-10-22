# Голосовой ассистент для задач и встреч

Каркас проекта. Сначала делаем **Telegram MVP**, после приёмки — **веб-версию с
backend и frontend** на том же API.

- Полный план: [`../PLAN.md`](../PLAN.md)
- Роли и контракт: [`ROLES.md`](ROLES.md)
- API: [`docs/api/README.md`](docs/api/README.md)
- Модели: [`docs/decisions/0003-api-first-models.md`](docs/decisions/0003-api-first-models.md)
- Локальный fallback: [`docs/decisions/0002-free-local-stack.md`](docs/decisions/0002-free-local-stack.md)

## Фазы

1. **Telegram MVP** — текст, голос, 4 обязательных сценария, напоминания.
2. **Web** — React-интерфейс, чат, таймлайн, поиск, голос в браузере.
3. **Полировка** — тесты, CI, README, демо.

Веб не начинаем, пока Telegram MVP не проходит 4 сценария.

## Стек

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic.
- **БД:** PostgreSQL 16/17, FTS `russian`, `pg_trgm`, опционально `pgvector`.
  В текущем демо-окружении `pgvector` недоступен, поэтому включён FTS + trigram;
  см. [`docs/decisions/0004-vector-search-deferred.md`](docs/decisions/0004-vector-search-deferred.md).
- **LLM:** API-first, OpenAI-compatible; fallback `RuleBasedLLM`; локальный Ollama — опция.
- **Telegram:** aiogram 3.x, long polling.
- **Голос:** Whisper API; локальный faster-whisper — опция; TTS — после MVP.
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

**Сначала связка — потом расширение.** Базовая интеграция уже собрана:

1. DTO и эндпоинты в `docs/api/README.md`.
2. `EventService`, `SearchService`, `DatetimeParser` — реальные A-сервисы.
3. `/chat`, `/voice` и `pending_actions` — через `assistant_tools.py`.
4. Маппинг Telegram `X-Telegram-Id` → `user_id` с проверкой `X-Bot-Secret`.

Дальше — 4 обязательных сценария, багфиксы и демо.

## Ветки

- `main` — стабильная ветка.
- `feat/core-*` — участник A.
- `feat/assistant-*` — участник B.
- Один PR — одна задача. Перед merge: тесты + self-review.
- `docker-compose.yml` и `.env.example` — B; `backend/app/main.py` — A,
  подключение B-роутеров согласуется в PR.
- `docs/api/README.md`, `PLAN.md`, ADR — только через PR.

## Ритм

- 10–15 минут утром: контракт и блокеры.
- 10 минут вечером: интеграция, 4 сценария, README.
- Любое изменение API — сначала сообщение, потом код.

## Критерий готовности каркаса

- Папки созданы, README описывает зоны.
- API-контракт зафиксирован.
- A может поднять БД и `/events` без бота.
- B может поднять бота на mock API без backend.
