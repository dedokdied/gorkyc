# Infra

Docker Compose и деплой. Владелец — B, backend/db-часть — A.

## Состав

```
infra/
├── docker/
│   ├── docker-compose.yml       # api, postgres, bot; frontend — этап 2
│   ├── Dockerfile.backend       # A
│   ├── Dockerfile.bot           # B
│   └── Dockerfile.frontend      # B, этап 2
└── deploy/
    ├── fly.toml                 # или render.yaml / railway.json
    └── env.example
```

## Docker Compose: Telegram MVP

- `postgres` — `pgvector/pgvector:pg16` с `pg_trgm` и `vector`.
- `api` — FastAPI, миграции Alembic, фоновый worker напоминаний.
- `bot` — aiogram, long polling, зависит от `api`.
- `frontend` — **не входит в Telegram MVP**, этап 5.

Публичный webhook боту не нужен: long polling. API наружу не публикуем,
бот ходит по внутренней сети.

```bash
cp .env.example .env
./scripts/deploy.sh
```

Или вручную:

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
docker compose -f infra/docker/docker-compose.yml ps
```

`Dockerfile.backend` применяет миграции и запускает `uvicorn`; `Dockerfile.bot`
устанавливает пакет бота. Compose готов к сборке, но локально Docker не
установлен, поэтому сборка образов ещё не проверялась.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | база в compose |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `TELEGRAM_BOT_TOKEN` | токен бота и отправка напоминаний |
| `BOT_INTERNAL_SECRET` | доверенный заголовок бота к API |
| `REMINDERS_ENABLED`, `REMINDERS_INTERVAL_SECONDS` | worker напоминаний |
| `BACKEND_URL` | URL API для бота |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | API-first или `rule-based` |
| `STT_PROVIDER`, `STT_API_KEY`, `STT_MODEL`, `STT_BASE_URL` | Whisper API или локальный faster-whisper |
| `TTS_PROVIDER` | `none` до этапа после MVP |
| `ENABLE_VECTOR_SEARCH` | включить pgvector |
| `ENABLE_RERANK` | включить reranker |
| `EMBEDDINGS_PROVIDER` | `local`, `api` или `off` |
| `APP_TZ` | таймзона по умолчанию |

Секреты — только в secrets хостинга, не в git.

## Деплой

### Telegram MVP

- VPS / Fly.io / Render: `api` + `postgres` + `bot`.
- Bot — long polling, без публичного порта.
- Postgres — managed или контейнер с volume.
- Healthchecks: `/api/v1/healthz`, `/api/v1/readyz`.
- Шаблон production-переменных: `infra/deploy/env.example`.
- Запуск на VPS: `./scripts/deploy.sh`.
- Приёмка: `python scripts/e2e/smoke.py`.

### Web (этап 2)

- Frontend — Vercel / Netlify / тот же VPS.
- Caddy — авто-TLS, прокси на `api` и `frontend`.
- `WEB_ORIGIN` и CORS.
- Демо-ссылка открывается без VPN.

## Definition of Done

- `docker compose up` поднимает Telegram MVP с нуля.
- Миграции применяются автоматически или одной командой.
- Бот отвечает в Telegram, напоминания приходят.
- Секреты не попадают в репозиторий.
- После этапа 2 открывается веб-демо.
