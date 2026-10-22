# Голосовой ассистент для задач и встреч — каркас проекта

Это рабочий каркас для тестового задания. Пока здесь только структура папок,
зоны ответственности и договорённости по параллельной работе. Код добавляется
поэтапно.

- Полный план: [`../PLAN.md`](../PLAN.md)
- Роли и график: [`ROLES.md`](ROLES.md)
- Контракт API: [`docs/api/README.md`](docs/api/README.md)

## Стек (кратко)

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2.
- **БД:** PostgreSQL 16/17, pgvector, pg_trgm, FTS `russian`.
  В текущем демо-окружении `pgvector` недоступен, поэтому включён FTS + trigram;
  см. [`docs/decisions/0002-vector-search-deferred.md`](docs/decisions/0002-vector-search-deferred.md).
- **LLM:** дешёвое API с tool calling через LiteLLM / OpenAI-compatible.
- **Голос:** faster-whisper + Silero VAD, TTS — edge-tts с fallback.
- **Frontend:** React + TypeScript + Vite, Tailwind, TanStack Query.
- **Инфраструктура:** Docker Compose; деплой — Fly.io / Render / Railway.

## Структура

```
project/
├── README.md                 # этот файл
├── ROLES.md                  # роли, владение файлами, план параллельной работы
├── .env.example              # переменные окружения без секретов
├── backend/
│   ├── README.md             # слои, интерфейсы, правила
│   ├── app/
│   │   ├── api/              # HTTP-роутеры
│   │   ├── core/             # конфиг, логирование, безопасность
│   │   ├── models/           # SQLAlchemy-модели
│   │   ├── schemas/          # Pydantic DTO и tool-схемы
│   │   ├── repositories/     # доступ к БД
│   │   ├── services/         # бизнес-логика
│   │   ├── integrations/     # LLM, STT, TTS, embeddings
│   │   └── workers/          # фоновые задачи
│   ├── migrations/           # Alembic
│   └── tests/                # backend-тесты
├── frontend/
│   ├── README.md             # страницы, компоненты, mock-режим
│   └── src/
│       ├── api/              # клиент API
│       ├── components/       # переиспользуемые компоненты
│       ├── hooks/            # хуки
│       ├── pages/            # экраны
│       ├── store/            # состояние
│       └── types/            # типы
├── infra/
│   ├── README.md             # Docker, деплой, env
│   ├── docker/               # compose, Dockerfile
│   └── deploy/               # конфиги хостинга
├── docs/
│   ├── README.md             # документация, ADR, демо-сценарий
│   ├── api/                  # контракт API
│   └── decisions/            # архитектурные решения (ADR)
├── scripts/
│   ├── README.md             # импорт CSV, seed, оценка поиска
│   └── ...
└── data/
    └── README.md             # описание датасета и правила импорта
```

## Главное правило параллельной работы

**Сначала контракт — потом код.** В первый час фиксируем:

1. Pydantic-схемы и эндпоинты в `docs/api/README.md`.
2. Интерфейсы `EventService`, `SearchService`, `DatetimeParser`.
3. Формат ответа `/chat` и структуру `pending_actions`.

После этого каждый работает в своих папках, не редактируя чужие файлы без
предупреждения.

## Ветки и слияние

- `main` — стабильная ветка, прямой push запрещён после первого коммита.
- `feat/core-*` — участник A.
- `feat/assistant-*` — участник B.
- Один PR — одна законченная задача. Перед merge: тесты + короткий self-review.
- Общие файлы (`pyproject.toml`, `docker-compose.yml`, `main.py`, `.env.example`)
  меняются только через отдельный PR или по договорённости.

## Ежедневный ритм

- 10–15 минут утром: синхронизация контракта и блокеров.
- 10 минут вечером: интеграция, проверка 4 сценариев, обновление README.
- Любое изменение контракта — сначала сообщение второму участнику, потом код.

## Критерий готовности каркаса

- Папки созданы, `.gitkeep` лежат в пустых директориях.
- `ROLES.md` и README описывают, кто что делает.
- Контракт API зафиксирован в `docs/api/README.md`.
- Оба участника могут начать работу, не ожидая друг друга.
