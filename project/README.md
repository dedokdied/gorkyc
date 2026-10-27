# Голосовой ассистент для задач и встреч

Telegram MVP и веб-версия работают на одном backend, одной доменной модели и
одном API. Бот — тонкий клиент, бизнес-логика не дублируется.

- Репозиторий: <https://github.com/dedokdied/gorkyc>
- Полный план: [`../PLAN.md`](../PLAN.md)
- Журнал изменений и текущее состояние: [`DEVLOG.md`](DEVLOG.md)
- API-контракт: [`docs/api/README.md`](docs/api/README.md)
- Web-версия: [`docs/web.md`](docs/web.md)
- Сценарий демо: [`docs/demo.md`](docs/demo.md)
- Тесты LLM по сценариям ТЗ: [`docs/llm-tests.md`](docs/llm-tests.md)
- Роли и границы: [`ROLES.md`](ROLES.md)
- Решения: [`docs/decisions/`](docs/decisions/)
- Инфраструктура: [`infra/README.md`](infra/README.md)

## Что готово

- 4 обязательных сценария: создание, уточнение, список, поиск.
- Список: today / tomorrow / week / upcoming / all, фильтр по типу
  (встречи, задачи, напоминания) и произвольный диапазон дат
  («с 3 по 7 ноября»).
- Прототип: <https://lustily-endowed-newfoundland.cloudpub.ru>. Для проверки
  достаточно зарегистрироваться по email; демо-пользователь `demo` с seed и
  CSV-корпусом доступен через API (`X-Demo-User`).
- Telegram: онбординг с меню, текст, голос (при настроенном STT),
  inline-уточнения, напоминания.
- Данные разделены по пользователю: бот использует Telegram-аккаунт
  (`from_user.id`), а не `chat.id`; события и поиск фильтруются по `user_id`.
- Ассистент помнит последние 12 сообщений диалога; полная история хранится в
  PostgreSQL и переживает рестарт и перезагрузку страницы.
- Web: регистрация и вход по email/паролю, чат, таймлайн с календарём и
  отдельной вкладкой выполненных, поиск, голосовой диалог (распознавание и
  озвучка ответов прямо в браузере), профиль с привязкой Telegram и таймзоной,
  in-app напоминания, монохромная мобильная вёрстка.
- Поиск: FTS `russian` + `pg_trgm` (падежи и опечатки).
- Напоминания: worker в backend + `TelegramNotifier` и баннер на сайте
  (`/reminders/inbox`). В профиле явно указано, что уведомления приходят в
  Telegram; после выбора режима сайт предлагает привязать бота.
- Повторяющиеся события: `daily`, `weekly`, `monthly`; следующий экземпляр
  создаётся при завершении.
- Персистентные уточнения: `pending_actions` и история диалога в PostgreSQL.
- CI: backend, bot, frontend build и Playwright e2e.
- Импорт CSV-корпуса и seed демо-данных.

## Соответствие ТЗ

| Сценарий ТЗ | Как реализовано |
|---|---|
| Создание задачи/напоминания | `create_event` + LLM tool calling; дата и время разбираются серверным `DatetimeParser`, ответ подтверждает содержание и срок |
| Создание встречи | `create_event` с типом `meeting`; проверка пересечений, длительность по умолчанию 60 минут |
| Список за период | `list_events`: сегодня, завтра, неделя, 30 дней, всё, произвольный диапазон и фильтр по типу |
| Поиск старых записей | PostgreSQL FTS `russian` + `pg_trgm`: падежи, опечатки и близкие формулировки; ищет и выполненные события |

Дополнительно: уточняющие вопросы, относительные даты («послезавтра», «через
два часа», «на следующей неделе»), повторяющиеся события, перенос/удаление,
отметка выполнения, защита от конфликтов встреч, несколько пользователей,
история диалога и веб-календарь.

## Ключевые решения

- **Один backend на Telegram и web.** Бот и сайт — тонкие клиенты к `/api/v1`,
  поэтому задачи, поиск и уточнения ведут себя одинаково.
- **LLM не считает даты.** Модель передаёт исходное выражение времени, а
  `DatetimeParser` детерминированно превращает его в `starts_at`/`due_at`.
  Это дешевле и надёжнее, чем доверять арифметику дат модели.
- **PostgreSQL + FTS/trigram.** Векторный поиск в прототипе не включён; FTS и
  `pg_trgm` дают поиск по падежам и опечаткам без внешних embedding-сервисов.
- **Голос в вебе — Web Speech API.** Распознавание и озвучка идут в браузере,
  без серверных ключей и загрузки аудио. Серверный STT остаётся для Telegram.
- **Уточнения хранятся в PostgreSQL.** `pending_actions` и история диалога
  переживают рестарт, а не теряются вместе с памятью процесса.
- **Fallback `RuleBasedLLM`.** Если провайдер недоступен, базовые сценарии
  продолжают работать без LLM, пусть и шаблонными ответами.

## Стек

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic.
- **БД:** PostgreSQL 16/17, FTS `russian`, `pg_trgm`, `btree_gist`.
- **LLM:** OpenAI-compatible API; fallback `RuleBasedLLM`.
- **Telegram:** aiogram 3.x, long polling.
- **Голос:** в вебе — Web Speech API (`SpeechRecognition` +
  `speechSynthesis`), без серверных ключей; в Telegram — серверный STT
  (Whisper API или локальный faster-whisper) по ключу. Серверный TTS не
  подключён.
- **Frontend:** React 18 + TypeScript + Vite, чистый CSS.
- **Web-auth:** email + password, PBKDF2, HMAC access token.
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

Открой `http://localhost:5173`, зарегистрируй аккаунт и создай первое
событие. Vite проксирует `/api` на `http://127.0.0.1:8000`. Подробности о
веб-версии, стеке и дизайне — в [`docs/web.md`](docs/web.md).

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

- `user_id` берётся только из auth-контекста: `Authorization: Bearer` для web,
  `X-Telegram-Id` + `X-Bot-Secret` для бота. `X-Demo-User` — только legacy/тесты
  при `ALLOW_DEMO_AUTH=true`. Не из тела запроса и не из аргументов LLM.
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
- Серверный TTS не реализован (`TTS_PROVIDER=none`): в вебе ответ
  озвучивает браузер, в Telegram голосовой ответ приходит текстом.
- Голос в Telegram требует `STT_API_KEY` (или локального `faster-whisper`);
  при `STT_PROVIDER=none` бот подсказывает перейти в текстовый режим.
- Веб-голос работает только в браузерах с Web Speech API (Chrome, Edge,
  Safari); в остальных доступен текстовый чат.
- `PendingActionStore` и история диалога хранятся в PostgreSQL; после рестарта
  уточнения и сообщения сохраняются.
- Web-auth — прототип: email/пароль и access-token в localStorage; refresh-
  токенов, подтверждения email и отзыва сессий пока нет.
- `X-Demo-User` оставлен для обратной совместимости тестов; в production
  выключается через `ALLOW_DEMO_AUTH=false`.
- Для production нужны реальные `TELEGRAM_BOT_TOKEN`, `LLM_API_KEY` и
  `STT_API_KEY`; без них доступны rule-based ответы и mock-режим бота.

## Что улучшил бы дальше

- **Надёжность LLM-слоя.** Сейчас при 429/таймауте включается rule-based
  fallback, поэтому ответы становятся шаблонными. Нужны несколько
  провайдеров, retry с backoff и кэш ответов.
- **Голос в Telegram.** Подключить серверный STT/TTS и отвечать голосом, а не
  только текстом; в вебе — потоковый синтез вместо браузерного.
- **Проверка дат.** Добавить больше естественных формулировок и часовых
  поясов, показывать «понял как …» перед созданием неоднозначного события.
- **Напоминания.** Web Push и уведомления в Telegram по расписанию, а не
  только in-app баннер при открытой вкладке.
- **Качество поиска.** Включить pgvector и rerank, когда появится embedding-
  провайдер; сейчас FTS + trigram.
- **Эксплуатация.** Refresh-токены и httpOnly cookie, метрики, трассировка
  запросов к LLM и алерты на рост ошибок.
