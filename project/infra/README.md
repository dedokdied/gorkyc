# Infra

Docker Compose и деплой. Владелец — B (деплой), backend/db-часть — A.

## Состав

```
infra/
├── docker/
│   ├── docker-compose.yml       # api, postgres, frontend
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── deploy/
    ├── fly.toml                 # или render.yaml / railway.json
    └── env.example              # что задать на хостинге
```

## Docker Compose (минимум ядра)

- `postgres:16` с расширениями `vector`, `pg_trgm`, `btree_gist`.
- `api` — FastAPI, зависит от postgres, healthcheck.
- `frontend` — статическая сборка Vite за Caddy/Nginx.
- Redis/worker — **не добавлять на старте**, только если реально нужны
  напоминания.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` | провайдер LLM |
| `STT_PROVIDER`, `TTS_PROVIDER` | голос |
| `ENABLE_VECTOR_SEARCH` | включить pgvector |
| `ENABLE_RERANK` | включить reranker |
| `EMBEDDINGS_PROVIDER` | `local`, `api` или `off` |
| `APP_TZ` | таймзона по умолчанию |

Секреты — только в secrets хостинга, не в git.

## Деплой

- Backend: Fly.io / Render / Railway / VPS.
- Postgres: Neon / Supabase (pgvector) или managed Postgres.
- Frontend: Vercel / Netlify / тот же VPS.
- Caddy — авто-TLS, прокси на api и frontend.
- Healthchecks: `/healthz`, `/readyz`.

## Definition of Done

- `docker compose up` поднимает проект с нуля.
- Миграции применяются автоматически или одной командой.
- Демо-ссылка открывается без VPN.
- Секреты не попадают в репозиторий.
