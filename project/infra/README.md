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

- `postgres:16` с расширениями `vector`, `pg_trgm`, `btree_gist`.
- `api` — FastAPI, миграции, APScheduler напоминаний.
- `bot` — aiogram, long polling, зависит от `api`.
- `frontend` — **не добавляем на MVP**, только на этапе 2.

Публичный webhook боту не нужен: long polling. API наружу не публикуем,
бот ходит по внутренней сети.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `TELEGRAM_BOT_TOKEN` | токен бота |
| `BOT_INTERNAL_SECRET` | доверенный заголовок бота к API |
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
- Healthchecks: `/healthz`, `/readyz`.

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
