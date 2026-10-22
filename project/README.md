# Голосовой ассистент для задач и встреч

Telegram MVP и веб-версия работают на одном backend, одной доменной модели и
одном API. Бот — тонкий клиент, бизнес-логика не дублируется.

- Полный план: [`../PLAN.md`](../PLAN.md)
- API-контракт: [`docs/api/README.md`](docs/api/README.md)
- Сценарий демо: [`docs/demo.md`](docs/demo.md)
- Роли и границы: [`ROLES.md`](ROLES.md)
- Решения: [`docs/decisions/`](docs/decisions/)
- Инфраструктура: [`infra/README.md`](infra/README.md)

## Что готово

- 4 обязательных сценария: создание, уточнение, список, поиск.
- Telegram: текст, голос, inline-уточнения, напоминания.
- Web: чат, таймлайн, поиск, карточки, редактирование, голосовой ввод,
  мобильная вёрстка.
- Поиск: FTS `russian` + `pg_trgm` (падежи и опечатки).
- Напоминания: worker в backend + `TelegramNotifier`.
- CI: backend, bot, frontend build и Playwright e2e.
- Импорт CSV-корпуса и seed демо-данных.

## Стек

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic.
- **БД:** PostgreSQL 16/17, FTS `russian`, `pg_trgm`, `btree_gist`.
- **LLM:** OpenAI-compatible API; fallback `RuleBasedLLM`.
- **Telegram:** aiogram 3.x, long polling.
- **Голос:** Whisper API; локальный faster-whisper — опция. TTS отложен.
- **Frontend:** React 18 + TypeScript + Vite.
- **Инфраструктура:** Docker Compose, nginx, GitHub Actions.

## Быстрый старт

Нужны Python 3.12+, Node 22+ и PostgreSQL 16+. Для PostgreSQL должны быть
доступны расширения `pg_trgm` и `btree_gist` (миграция создаёт их сама).

```bash
cd project
cp .env.example .env
createdb assistant
```

Отредактируй `DATABASE_URL` в `.env`, если у тебя другой пользователь/пароль.
Для демо без внешних ключей поставь в `.env`:

```env
LLM_PROVIDER=rule-based
TTS_PROVIDER=none
```

### Backend

```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Проверка: `http://localhost:8000/api/v1/healthz`.

Миграции — единственный способ менять схему; `create_all` в runtime не
используется.

### Web

```bash
cd project/frontend
npm ci
npm run dev
```

Открой `http://localhost:5173`. Vite проксирует `/api` на
`http://127.0.0.1:8000`. Demo-пользователя можно переключить в шапке; по
умолчанию — `demo`.

### Telegram-бот

```bash
cd project/telegram_bot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m app.main
```

В `.env` задай `TELEGRAM_BOT_TOKEN`, `BACKEND_URL` и `BOT_INTERNAL_SECRET`.
Для проверки UI без backend: `BOT_MOCK_MODE=true`.

### Docker Compose

```bash
cd project
cp infra/deploy/env.example .env
docker compose -f infra/docker/docker-compose.yml up -d --build
```

Web — `http://localhost:8080`, API — `http://localhost:8000`. Compose
собирает postgres, api, bot и web; nginx проксирует `/api/` на `api:8000`.

## Demo-данные

Seed создаёт пользователя `demo` и пять событий относительно текущей даты:

```bash
cd project
python scripts/seed_demo.py --user demo
```

Импорт CSV-корпуса (1000 событий, источник `import`):

```bash
python scripts/import_csv.py --dry-run
python scripts/import_csv.py --user demo
```

CSV ищется в `project/data/`, затем в корне репозитория; путь можно задать
через `--csv`.

Скрипт читает UTF-8 с BOM, классифицирует записи и идемпотентен по
`(title, datetime)`. Повторный запуск не создаёт дубли. Встречи импортируются
по 15 минут, чтобы соседние слоты корпуса не нарушали запрет пересечений.
Датасет — seed/корпус для поиска, не «боевые» данные пользователя.

## Тесты

```bash
# Backend: отдельная БД assistant_test создаётся автоматически
cd project/backend
pytest -q
ruff check app tests

# Bot
cd project/telegram_bot
pytest -q
ruff check app tests

# Frontend
cd project/frontend
npm run build
```

Browser e2e требует запущенный backend и PostgreSQL. Playwright сам поднимает
Vite dev server:

```bash
cd project/frontend
npm ci
npx playwright install --with-deps chromium   # Linux/CI
npm run e2e
```

Локально на Windows можно использовать установленный Edge:
`PLAYWRIGHT_CHANNEL=msedge npm run e2e` (это дефолт вне CI).

Проверка API из командной строки:

```bash
cd project
python scripts/e2e/smoke.py
python scripts/e2e/smoke.py --voice-file samples/voice.ogg
```

CI в `.github/workflows/ci.yml` поднимает PostgreSQL, применяет миграции,
запускает backend/bot-тесты, сборку frontend и browser e2e.

## Структура

```
project/
├── backend/
│   ├── app/
│   │   ├── api/              # events, search, chat, voice, health
│   │   ├── core/             # конфиг, логи, middleware
│   │   ├── models/           # SQLAlchemy
│   │   ├── schemas/          # Pydantic DTO и tool-схемы
│   │   ├── repositories/     # SQL-запросы
│   │   ├── services/         # домен, даты, поиск, диалог
│   │   ├── integrations/     # LLM, STT, TTS, Telegram notifier
│   │   └── workers/          # scheduler напоминаний
│   ├── migrations/
│   └── tests/
├── telegram_bot/
├── frontend/
│   ├── src/
│   └── e2e/                  # Playwright
├── scripts/
│   ├── import_csv.py
│   ├── seed_demo.py
│   └── e2e/
├── infra/
│   ├── docker/
│   └── deploy/
├── docs/
└── data/
```

## Правила разработки

- `user_id` берётся только из auth-контекста: `X-Telegram-Id` +
  `X-Bot-Secret` для бота или `X-Demo-User` для web. Не из тела запроса и не
  из аргументов LLM.
- Backend не импортирует aiogram, кроме `TelegramNotifier`.
- Бот не содержит SQL и бизнес-логики.
- LLM не считает даты: серверный `DatetimeParser` превращает
  `time_expression` в `starts_at`/`due_at`.
- API меняется сначала в `docs/api/README.md`, потом в коде.
- Все даты в БД — `timestamptz` (UTC), отображение — в таймзоне пользователя.
- Секреты не коммитятся; `.env` в `.gitignore`.

## Ограничения

- `pgvector` в демо-окружении недоступен: работает FTS + trigram, векторный
  поиск выключен (`docs/decisions/0004-vector-search-deferred.md`).
- TTS не реализован (`TTS_PROVIDER=none`).
- `PendingActionStore` in-memory; после рестарта незавершённые уточнения
  теряются.
- Для production нужны реальные `TELEGRAM_BOT_TOKEN`, `LLM_API_KEY` и
  `STT_API_KEY`; без них доступны rule-based ответы и mock-режим бота.
- Docker-образы описаны, но локально не собирались (Docker не установлен).
