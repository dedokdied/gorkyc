# План проекта: голосовой ассистент для задач и встреч

## 1. Решение

Сначала делаем **MVP в Telegram**, затем — **полноценную веб-версию с backend и frontend**.

Оба этапа используют **один backend** и одну доменную модель. Telegram-бот — это
тонкий клиент к API, а не отдельная реализация логики. Веб-версия позже
подключается к тому же API, поэтому бизнес-логика, даты, поиск и БД не
дублируются.

OpenClaw в проекте **не используется**. Старый OpenClaw-план отменён.

```
Telegram bot ─┐
              ├──> FastAPI backend ──> PostgreSQL
React web ────┘         │
                        ├──> LLM API (tool calling)
                        ├──> STT/TTS
                        └──> scheduler напоминаний
```

## 2. Этапы

| Этап | Что делаем | Результат |
|---|---|---|
| 0. Каркас | контракт API, БД, skeleton, env | оба могут работать параллельно |
| 1. Telegram MVP | backend core + бот + текст | 4 сценария в Telegram |
| 2. Ассистент | LLM, tools, даты, уточнения | свободные формулировки |
| 3. Голос и поиск | voice notes, STT/TTS, FTS/trigram | голосовой сценарий |
| 4. Приёмка MVP | тесты, деплой, демо | рабочая ссылка на бота |
| 5. Web | React + API + voice | сайт с беком и фронтом |
| 6. Полировка | e2e, README, demo | финальная сдача |

**Правило:** веб начинаем только после того, как Telegram MVP проходит
4 обязательных сценария. Иначе распылимся и не сдадим ничего.

## 3. Обязательные сценарии

1. Создать задачу/встречу/напоминание свободной фразой.
2. Уточнить недостающие поля: «Поставь встречу с Иваном завтра» → «Во сколько?».
3. Показать список на период: «Что у меня завтра?».
4. Найти старые записи: «Найди задачи про договор».

Дополнительно: изменить, выполнить, удалить, перенести, голосовой ввод,
напоминание в нужное время.

## 4. Стек

| Слой | Выбор |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| ORM/БД | SQLAlchemy 2.0 async + asyncpg, Alembic |
| БД | PostgreSQL 16/17 |
| Поиск | FTS `russian`, `pg_trgm`, опционально `pgvector` |
| LLM | LiteLLM / OpenAI-compatible API, tool calling |
| Telegram | aiogram 3.x, long polling на MVP |
| STT | faster-whisper локально или Whisper/Groq API |
| TTS | edge-tts, опционально |
| Frontend (этап 5) | React + TypeScript + Vite, TanStack Query |
| Напоминания | APScheduler + PostgreSQL job store |
| Инфраструктура | Docker Compose, VPS/Fly.io/Render |
| Качество | ruff, mypy, pytest; frontend — eslint/tsc |

## 5. Архитектура

```
backend/
  api/            HTTP-роутеры: events, search, chat, voice, health
  services/       бизнес-логика, не знает про Telegram и FastAPI
  repositories/   SQL-запросы
  models/         SQLAlchemy
  schemas/        Pydantic DTO и tool-схемы
  integrations/   LLM, STT, TTS, Telegram notifier
  workers/        scheduler напоминаний

telegram_bot/
  handlers/       /start, текст, голос, кнопки
  api_client.py   HTTP-клиент к backend
  keyboards.py    inline-кнопки
  config.py       токен и URL backend

frontend/         React-приложение (этап 5)
```

Правила:

- Telegram-бот не содержит SQL и бизнес-логики.
- Backend не импортирует aiogram, кроме `TelegramNotifier`.
- LLM не хранит задачи и не считает даты.
- Все каналы работают через один сервисный слой.

## 6. Модель данных

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE event_type AS ENUM ('task', 'meeting', 'reminder');
CREATE TYPE event_status AS ENUM ('planned', 'done', 'cancelled');
CREATE TYPE event_source AS ENUM ('text', 'voice', 'import');
CREATE TYPE chat_channel AS ENUM ('telegram', 'web');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'tool');

CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id   bigint UNIQUE,
    email         text UNIQUE,
    display_name  text NOT NULL,
    timezone      text NOT NULL DEFAULT 'Europe/Moscow',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel       chat_channel NOT NULL,
    external_id   text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_activity_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (channel, external_id)
);

CREATE TABLE messages (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role          message_role NOT NULL,
    content       text NOT NULL,
    tool_name     text,
    tool_payload  jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type          event_type NOT NULL,
    status        event_status NOT NULL DEFAULT 'planned',
    title         text NOT NULL,
    description   text,
    starts_at     timestamptz,
    ends_at       timestamptz,
    due_at        timestamptz,
    duration_minutes integer,
    timezone      text NOT NULL DEFAULT 'Europe/Moscow',
    source        event_source NOT NULL DEFAULT 'text',
    recurrence    text,
    parent_id     uuid REFERENCES events(id) ON DELETE SET NULL,
    metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
    search_text   text NOT NULL DEFAULT '',
    tsv           tsvector GENERATED ALWAYS AS
                  (to_tsvector('russian', search_text)) STORED,
    embedding     vector(1024),
    reminder_sent_at timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    completed_at  timestamptz,
    CONSTRAINT events_time_check CHECK (
        starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at
    ),
    CONSTRAINT meetings_time_check CHECK (
        type <> 'meeting' OR (starts_at IS NOT NULL AND ends_at IS NOT NULL)
    ),
    CONSTRAINT events_duration_check CHECK (
        duration_minutes IS NULL OR duration_minutes > 0
    )
);

CREATE INDEX events_user_time_idx ON events (user_id, starts_at);
CREATE INDEX events_user_due_idx  ON events (user_id, due_at);
CREATE INDEX events_tsv_idx       ON events USING gin (tsv);
CREATE INDEX events_trgm_idx      ON events USING gin (search_text gin_trgm_ops);
CREATE INDEX events_embedding_idx ON events
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

ALTER TABLE events ADD CONSTRAINT meetings_no_overlap
EXCLUDE USING gist (
    user_id WITH =,
    tstzrange(starts_at, ends_at, '[)') WITH &&
) WHERE (type = 'meeting' AND status = 'planned' AND starts_at IS NOT NULL);

CREATE TABLE pending_actions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intent        text NOT NULL,
    slots         jsonb NOT NULL DEFAULT '{}'::jsonb,
    missing       text[] NOT NULL DEFAULT '{}',
    last_entity_id uuid REFERENCES events(id) ON DELETE SET NULL,
    is_active     boolean NOT NULL DEFAULT true,
    expires_at    timestamptz NOT NULL DEFAULT now() + interval '30 minutes',
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX pending_one_active_idx
    ON pending_actions (session_id) WHERE is_active;
```

Правила:

- Для встречи `starts_at` и `ends_at` обязательны; `duration_minutes` — вход,
  backend сам считает `ends_at`.
- Для напоминания `due_at` обязателен.
- Пересечение встреч запрещено на уровне БД.
- `session_id` для Telegram — внутренняя сессия backend, `external_id` — chat_id.
- `user_id` берётся из auth/канала, никогда из аргументов LLM.
- `reminder_sent_at` защищает от повторной отправки напоминания.

## 7. API

Базовый префикс: `/api/v1`. Контракт: `project/docs/api/README.md`.

| Метод | Путь | Назначение |
|---|---|---|
| GET/POST | `/events` | список и создание |
| GET/PATCH/DELETE | `/events/{id}` | чтение, правка, удаление |
| POST | `/events/{id}/complete` | выполнить |
| POST | `/search` | поиск |
| POST | `/chat` | текст → ответ ассистента |
| POST | `/voice` | аудио → расшифровка → ответ |
| GET | `/sessions/{id}/messages` | история |
| POST | `/clarifications/{id}/answer` | ответ на уточнение |
| GET | `/healthz`, `/readyz` | health |

Авторизация MVP:

- Telegram: backend получает `X-Telegram-Id` и `X-Bot-Secret` от бота.
- Web: `X-Demo-User: demo`.
- Позже: JWT без изменения остальных DTO.

## 8. LLM и tools

LLM — оркестратор. Она извлекает intent, тип, название и `time_expression`,
но не считает даты.

```text
create_event
update_event
complete_event
delete_event
list_events
search_events
ask_clarification
get_current_datetime
```

Правила:

- Аргументы валидируются Pydantic.
- `time_expression` → `starts_at`/`due_at` на сервере.
- `duration_expression` → `ends_at`.
- При нехватке слота tool сохраняет `pending_action` и возвращает
  `needs_clarification`.
- Модель не получает `user_id` и не может его подменить.
- Не более 1–2 tool calls на реплику.
- Для болтовни — отдельный режим без tools.

## 9. Даты и NLU

1. Нормализация текста после STT.
2. LLM извлекает слоты и исходные временные выражения.
3. Серверный `DatetimeParser`:
   - `dateparser` с локалью `ru` и `RELATIVE_BASE`;
   - `zoneinfo` для таймзоны и UTC;
   - правила для «до конца недели», «в пятницу», «через два часа»;
   - проверка диапазонов.
4. При неоднозначности — уточнение, а не догадка.

Политика:

| Фраза | Трактовка |
|---|---|
| `завтра` | +1 день |
| `в пятницу` | ближайшая будущая пятница |
| `через два часа` | now + 2h |
| `до конца недели` | воскресенье 23:59 |
| `утром/днём/вечером` | 09:00 / 13:00 / 18:00 + подтверждение |
| дата без времени | уточнить время |

Все даты хранятся в UTC, отображаются в таймзоне пользователя.

## 10. Telegram MVP

Бот — основной интерфейс первого этапа.

- `/start` — регистрация, таймзона, приветствие.
- Текст — отправка в `/chat`, ответ с подтверждением или уточнением.
- Голосовое сообщение — скачать OGG, отправить в `/voice`, показать расшифровку.
- `/today`, `/tomorrow`, `/week` — быстрый список.
- `/search` — поиск по старым задачам.
- `/settings` — таймзона и TTS.
- Inline-кнопки для уточнений: «Сегодня», «Завтра», «10:00», «15:00».
- Подтверждение: «Создал встречу: завтра, 15:00 — Иван».
- Ошибки — понятным текстом, без stack trace.
- Текстовый ввод всегда доступен, даже если голос не распознан.

MVP работает через long polling, без публичного webhook. Это проще для локальной
разработки и деплоя.

## 11. Напоминания

- `events` с `type='reminder'` и `due_at`.
- APScheduler в backend с PostgreSQL job store.
- Раз в 30–60 секунд scheduler выбирает просроченные напоминания.
- Отправка через `TelegramNotifier` (Bot API) по `users.telegram_id`.
- После отправки выставляется `reminder_sent_at`.
- Для веб-этапа тот же scheduler; уведомление можно показывать в UI.
- Redis/ARQ не добавляем, пока MVP не стабилен.

## 12. Поиск

Порядок:

1. Точный текст по `title`/`description`.
2. FTS `russian`.
3. `pg_trgm` для опечаток и падежей.
4. При флаге — embeddings + pgvector.
5. RRF/rerank — только после стабильного MVP.

Флаги: `ENABLE_VECTOR_SEARCH`, `ENABLE_RERANK`, `EMBEDDINGS_PROVIDER`.
Если вектор отключён, поиск всё равно работает на FTS + trigram.

Датасет `voice_assistant_events_1000_*.csv`: seed и golden-set, не «боевые»
данные пользователя.

## 13. Web-этап

После приёмки Telegram MVP:

- React + TypeScript + Vite.
- Страницы: чат, таймлайн, поиск, настройки.
- Карточки событий, редактирование распознанных полей, быстрые уточнения.
- Голос: MediaRecorder → `/voice`; текст всегда доступен.
- История сессии через `/sessions/{id}/messages`.
- Адаптивная вёрстка, демо с телефона.
- Тот же backend и те же tools; никакой второй бизнес-логики.
- Demo-user; позже JWT.

## 14. Роли

Подробно — в `project/ROLES.md`.

- **A — Backend Core / Data & API:** БД, миграции, события, даты, поиск,
  `/events`, `/search`, импорт CSV, доменные тесты, scheduler.
- **B — Assistant / Telegram & Web UX:** LLM, tools, диалог, `/chat`, `/voice`,
  STT/TTS, Telegram-бот, frontend, деплой, e2e.

Общие зоны: контракт API, `docker-compose.yml`, README, демо-сценарий.

## 15. График

| Этап | Часы (на двоих) |
|---|---:|
| 0. Контракт и каркас | 2 |
| 1. Backend core + текст в Telegram | 6 |
| 2. LLM/tools/даты/уточнения | 5 |
| 3. Голос, напоминания, поиск | 5 |
| 4. Приёмка и деплой Telegram MVP | 4 |
| 5. Web frontend + интеграция | 8 |
| 6. Тесты, README, демо | 4 |
| **Итого** | **34** |

Это ориентир. Если время сжимается, сначала закрываем этапы 0–4, потом веб.

## 16. Definition of Done

### Telegram MVP

- 4 обязательных сценария работают end-to-end.
- Текст и голосовое сообщение.
- Уточняющий диалог с inline-кнопками.
- Данные сохраняются после перезапуска.
- Поиск по падежам и опечаткам.
- Напоминание реально приходит.
- Демо-бот открывается по ссылке.
- README поднимает проект с нуля.

### Web

- Те же 4 сценария в браузере.
- Чат, таймлайн, поиск, карточки, редактирование.
- Голосовой ввод и текстовая альтернатива.
- Мобильная вёрстка.
- Демо-ссылка без VPN.

## 17. Риски

| Риск | Mitigation |
|---|---|
| Распыление на веб до MVP | жёсткий gate после 4 сценариев |
| LLM выдумывает даты | `time_expression` + серверный парсер |
| Плохой русский STT | API Whisper/Groq, текстовый fallback |
| Дублирование логики бот/веб | один backend, бот — тонкий клиент |
| Повторные напоминания | `reminder_sent_at` + lock |
| Лимиты Telegram | короткие ответы, разбиение длинных сообщений |
| Расхождение API | сначала `docs/api/README.md`, потом код |
| Нехватка времени | сначала Telegram MVP, веб — после |

## 18. Переменные окружения

```env
APP_ENV=dev
APP_TZ=Europe/Moscow
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/assistant

TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
BOT_MODE=polling
BACKEND_URL=http://localhost:8000/api/v1
BOT_INTERNAL_SECRET=

LLM_PROVIDER=openai
LLM_API_KEY=
LLM_MODEL=
LLM_BASE_URL=

STT_PROVIDER=faster-whisper
STT_API_KEY=
TTS_PROVIDER=edge-tts

ENABLE_VECTOR_SEARCH=false
ENABLE_RERANK=false
EMBEDDINGS_PROVIDER=off

WEB_ORIGIN=http://localhost:5173
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_MOCKS=true
```

## 19. Демо

1. Открыть Telegram-бота.
2. «Напомни завтра в 10 позвонить Ивану».
3. «Поставь встречу с Иваном завтра» → «В 15:00».
4. «Что у меня завтра?».
5. «Найди задачи про договор».
6. Голосовое сообщение с той же фразой.
7. Показать, что данные сохранились после перезапуска.
8. После веб-этапа повторить в браузере.

## 20. Что не делаем на MVP

- Свой React-фронт до приёмки Telegram.
- Redis/ARQ и отдельный worker.
- Полный auth/JWT.
- Сложные recurring-правила.
- Свой мобильный клиент.
- Микросервисы.
