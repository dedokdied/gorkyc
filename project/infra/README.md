# Infra

Docker Compose и деплой. Владелец — B, backend/db-часть — A.

## Состав

```
infra/
├── docker/
│   ├── docker-compose.yml       # postgres, api, bot, web
│   ├── Dockerfile.backend       # A
│   ├── Dockerfile.bot           # B
│   ├── Dockerfile.frontend      # B
│   └── nginx.conf               # статика + прокси /api
└── deploy/
    ├── fly.toml                 # или render.yaml / railway.json
    └── env.example
```

## Docker Compose

- `postgres` — `pgvector/pgvector:pg16` с `pg_trgm` и `vector`.
- `api` — FastAPI, миграции Alembic, фоновый worker напоминаний.
- `bot` — aiogram, long polling, зависит от `api`.
- `web` — production-сборка frontend на nginx, порт `${WEB_PORT:-8080}`;
  `nginx` проксирует `/api/` на `api:8000`.

Публичный webhook боту не нужен: long polling. Web и бот ходят к API по
внутренней сети; для локальной разработки API опубликован на `8000`.

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

## CI

`.github/workflows/ci.yml` на каждый push/PR:

- поднимает PostgreSQL 16 и проверяет миграции;
- запускает backend- и bot-тесты, `ruff`;
- собирает frontend;
- запускает Playwright e2e против реального API.

Docker-образы в CI не собираются: для этого нужен отдельный job с Docker
daemon.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | база в compose |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `TELEGRAM_BOT_TOKEN` | токен бота и отправка напоминаний |
| `BOT_INTERNAL_SECRET` | доверенный заголовок бота к API |
| `REMINDERS_ENABLED`, `REMINDERS_INTERVAL_SECONDS`, `REMINDERS_GRACE_MINUTES` | worker уведомлений: период опроса и окно досылки |
| `BACKEND_URL` | URL API для бота |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | API-first или `rule-based` |
| `STT_PROVIDER`, `STT_API_KEY`, `STT_MODEL`, `STT_BASE_URL` | Whisper API или локальный faster-whisper |
| `TTS_PROVIDER` | `none` до этапа после MVP |
| `ENABLE_VECTOR_SEARCH` | включить pgvector |
| `ENABLE_RERANK` | включить reranker |
| `EMBEDDINGS_PROVIDER` | `local`, `api` или `off` |
| `WEB_ORIGIN` | origin(ы) web-клиента для CORS через запятую |
| `WEB_PORT` | порт web-контейнера, по умолчанию `8080` |
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

### Web

- `web` — nginx со статикой; `/api/` проксируется на `api:8000`, поэтому в
  compose CORS для same-origin запросов не нужен.
- При отдельном размещении frontend (Vercel/Netlify) задать `WEB_ORIGIN` на
  backend и `VITE_API_BASE_URL` на frontend.
- Caddy/ingress — авто-TLS перед `web`.
- Демо-ссылка открывается без VPN.

## Definition of Done

- `docker compose up` поднимает Telegram MVP и web с нуля.
- Миграции применяются автоматически или одной командой.
- Бот отвечает в Telegram, напоминания приходят.
- Секреты не попадают в репозиторий.
- Web-демо открывается на `WEB_PORT` и ходит в API через nginx.
