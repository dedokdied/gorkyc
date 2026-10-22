# План реализации: голосовой ассистент для задач и встреч

> Документ-основа для тестового задания. Здесь: краткий разбор задания, архитектура,
> рекомендуемый стек, модель данных, идеи по NLU/поиску/контексту, библиотеки,
> этапы работ и приоритеты: сначала стабильное ядро из 4 сценариев, затем контекст,
> поиск, голос и только потом инфраструктура и бонусы.

---

## 1. Задание кратко

### Цель

Прототип голосового ассистента, который помогает управлять личными задачами,
напоминаниями и встречами. Пользователь обращается голосом или текстом в свободной
форме и получает текстовый или голосовой ответ. Главный акцент — **логика
ассистента**, а не интерфейс: понимание запроса, работа с данными, корректное
выполнение действий.

### Обязательные сценарии (4)

1. **Создание задачи/напоминания**
   - «Напомни мне завтра в 10 утра позвонить Ивану».
   - «В пятницу нужно отправить отчёт».
   - «Поставь задачу купить билеты до конца недели».
   - Определить содержание, дату/время (если есть), сохранить, подтвердить.

2. **Создание встречи**
   - «Добавь встречу с командой завтра в 15:00».
   - «В четверг в 11 у меня встреча с дизайнером».
   - Определить название/содержание, дату/время, сохранить.

3. **Получение информации о предстоящих событиях**
   - «Что у меня сегодня?»
   - «Есть ли у меня встречи сегодня?»
   - «Какие задачи у меня на завтра?»
   - «Что запланировано на эту неделю?»

4. **Поиск ранее созданных записей**
   - «Найди задачу про презентацию».
   - «Когда у меня была встреча с Иваном?»
   - «Я когда-то ставил задачу по договору, найди её».
   - Точное совпадение формулировок не требуется; желателен поиск по смыслу.

### Требования к естественному языку

- Свободные формулировки, без жёстких команд.
- Синонимичные запросы трактуются одинаково:
  «Что у меня сегодня?» = «Какие планы на сегодня?» = «Покажи мои встречи на сегодня».
- Относительные даты: `сегодня`, `завтра`, `послезавтра`, `в пятницу`,
  `через два часа`, `на следующей неделе`.
- Если данных не хватает — уточняющий вопрос:
  - Пользователь: «Поставь встречу с Иваном завтра».
  - Ассистент: «На какое время поставить встречу?»

### Хранение

Для каждой записи желательно хранить:

- тип: задача / встреча / напоминание;
- название или текст;
- дату и время;
- дату создания;
- статус выполнения (при необходимости).

Данные должны сохраняться между запросами. Способ хранения — на выбор кандидата.

### Голосовой интерфейс

Минимальный цикл:

```
голос → STT → обработка запроса → действие → ответ (TTS или текст)
```

Разрешены готовые API и библиотеки для STT, TTS и LLM. Интерфейс может быть
минимальным: кнопка записи, история диалога, ответ ассистента.

### Что сдать

1. Ссылка на репозиторий с исходным кодом.
2. README с инструкцией по запуску.
3. Краткое описание архитектуры и выбранных технологий.
4. Ссылка на работающий прототип.

В README также описать самостоятельные решения и то, что улучшили бы при наличии
времени.

### Критерии оценки

- **Работоспособность** — стабильность основных сценариев.
- **Качество понимания** — свободные формулировки, а не только команды.
- **Архитектура** — разделение голоса, LLM, бизнес-логики и хранения.
- **Работа с данными** — корректность создания, получения и поиска.
- **Качество кода** — структура, читаемость, обоснованность решений.
- **UX** — естественность диалога, включая уточняющие вопросы.

### Бонусы (не обязательны)

- изменение и удаление задач голосом;
- отметка задачи выполненной;
- обработка конфликтующих встреч;
- повторяющиеся задачи и встречи;
- контекст диалога («А перенеси её на завтра»);
- семантический поиск по старым задачам;
- интеграция с реальным календарём;
- поддержка нескольких пользователей;
- обработка неоднозначных запросов и уточняющий диалог.

### Что разрешено

- Любой язык, стек, БД, формат UI.
- Готовые API и библиотеки для STT/TTS/LLM.
- AI-инструменты при разработке.
- Локальная LLM не требуется — дешёвое API допустимо.

### Приоритеты реализации

1. Стабильные 4 обязательных сценария.
2. Уточняющий диалог и контекст через `pending_actions`.
3. Поиск: сначала FTS + trigram, затем (по флагу) векторный.
4. Голос: STT/TTS с обязательным текстовым fallback.
5. Бонусы и инфраструктура (Redis/ARQ, полный auth, мониторинг) — только после
   стабильного ядра.

---

## 2. Ключевая идея решения

**LLM понимает и вызывает инструменты, БД хранит правду, бизнес-логика валидирует.**

Нельзя строить ассистента так, чтобы модель «помнила» задачи или придумывала даты.
Правильный контур:

```
текст/голос
   ↓
STT (если голос)
   ↓
LLM: intent + слоты + time_expression → tool call (строгая JSON-схема)
   ↓
валидация Pydantic + серверный DatetimeParser
   ↓
доменный сервис → PostgreSQL
   ↓
ответ (текст + опционально TTS)
```

Ключевые принципы:

1. **LLM — оркестратор, а не хранилище.** Все задачи/встречи читаются и пишутся
   только через инструменты и БД.
2. **Гибридный NLU.** LLM извлекает intent, тип, название и исходное временное
   выражение (`time_expression`); `dateparser`/правила резолвят даты на сервере,
   Pydantic проверяет аргументы. Модель не возвращает готовые ISO-даты как истину.
3. **Даты резолвит сервер.** `time_expression` → конкретные `starts_at`/`due_at`
   в таймзоне пользователя; при неоднозначности — уточняющий вопрос.
4. **Структурированный контекст.** В БД лежат не только сообщения, но и состояние
   диалога: `pending_action`, незаполненные слоты, `last_entity_id`, таймзона.
5. **Уточнение вместо выдумывания.** Не хватает времени/даты — задать вопрос и
   сохранить незавершённое намерение.
6. **Гибридный поиск.** Сначала лексика (FTS + trigram), затем по флагу векторный
   поиск и rerank. Только embeddings на коротких русских фразах работает нестабильно.
7. **Деградация без LLM.** Простые команды (`что сегодня`) можно обработать
   правилами, если провайдер недоступен.

---

## 3. Архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│  Frontend: React + TypeScript + Vite                             │
│  микрофон, история диалога, карточки событий, поиск, настройки   │
└───────────────┬──────────────────────────────────────────────────┘
                │ HTTPS / SSE / WebSocket
┌───────────────▼──────────────────────────────────────────────────┐
│  API: FastAPI                                                     │
│  ├── auth / users                                                 │
│  ├── chat (text, voice, streaming)                                │
│  ├── events CRUD + list                                           │
│  ├── search                                                       │
│  └── health / metrics                                             │
├──────────────────────────────────────────────────────────────────┤
│  Application / domain                                             │
│  ├── DialogueService      — контекст, pending actions, уточнения  │
│  ├── NLUService           — LLM tool calling + разбор дат         │
│  ├── EventService         — задачи/встречи/напоминания            │
│  ├── SearchService        — hybrid search + rerank                │
│  └── NotificationService  — напоминания (бонус)                   │
├──────────────────────────────────────────────────────────────────┤
│  Integrations                                                     │
│  ├── LLM (LiteLLM / OpenAI-compatible, fallback на локальную)    │
│  ├── STT (faster-whisper / API)                                   │
│  ├── TTS (edge-tts / Silero / API)                                │
│  └── Embeddings (bge-m3 / API)                                    │
└───────────────┬──────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────┐
│  PostgreSQL 16+                                                   │
│  ├── pgvector       — эмбеддинги событий                          │
│  ├── pg_trgm        — нечёткий лексический поиск                  │
│  ├── FTS russian    — полнотекстовый поиск                        │
│  ├── btree_gist     — запрет пересечения встреч                   │
│  └── JSONB          — слоты, метаданные, состояние диалога        │
└───────────────┬──────────────────────────────────────────────────┘
                │
        ┌───────▼────────┐        ┌─────────────────────┐
        │ Redis (опц.)   │        │ Worker (ARQ)        │
        │ кэш, лимиты,   │        │ напоминания,         │
        │ очередь         │        │ эмбеддинги, импорт   │
        └────────────────┘        └─────────────────────┘
```

### Разделение слоёв

| Слой | Ответственность | Не должен знать |
|---|---|---|
| `api/` | HTTP, валидация входа, auth, SSE | про SQL и промпты |
| `services/` | бизнес-правила, сценарии | про FastAPI и ORM-детали |
| `repositories/` | доступ к БД | про LLM |
| `integrations/` | LLM, STT, TTS, embeddings | про доменные правила |
| `models/` | SQLAlchemy-модели | про HTTP |
| `schemas/` | Pydantic DTO и tool-схемы | про БД |
| `workers/` | фоновые задачи | про HTTP-сессию |

---

## 4. Рекомендуемый стек

### Backend

| Задача | Выбор | Почему |
|---|---|---|
| Язык | Python 3.12+ | Лучшая экосистема для LLM/STT, быстрый старт |
| API | FastAPI | async, OpenAPI, SSE/WebSocket, typed |
| Валидация | Pydantic v2 | те же схемы для API и tool calling |
| ORM | SQLAlchemy 2.0 (async) | зрелость, типизация, миграции |
| Миграции | Alembic | стандарт, ревьюируемые миграции |
| Драйвер | asyncpg | быстрый async-доступ к PostgreSQL |
| Настройки | pydantic-settings | типизированный `.env` |
| Логи | structlog | структурные JSON-логи, request_id |
| Фон | `BackgroundTasks`/APScheduler на старте, ARQ + Redis — после ядра | очередь нужна только для реальных напоминаний |
| Тесты | pytest + pytest-asyncio + httpx + testcontainers | unit/integration/e2e |
| Качество | ruff + mypy + pre-commit | линт, формат, типы |
| CI | GitHub Actions | тесты, линт, сборка образа |

> На этапе ядра Redis, ARQ, полный auth и мониторинг не нужны: demo-user,
> синхронные эмбеддинги или `BackgroundTasks`. Инфраструктура подключается после
> стабильных 4 сценариев.

### Данные

| Компонент | Выбор | Комментарий |
|---|---|---|
| Основная БД | **PostgreSQL 16/17** | реляционная модель + ограничения целостности |
| Векторы | **pgvector** (HNSW, cosine) | не нужен отдельный vector DB |
| Нечёткий поиск | **pg_trgm** | опечатки, падежи, короткие фразы |
| Полнотекст | **FTS `russian`** | точные слова, ранжирование |
| Пересечения встреч | **btree_gist + EXCLUDE** | конфликт на уровне БД, а не в коде |
| JSONB | слоты и метаданные | гибкость без потери схемы |
| Redis (опц.) | кэш, rate limit, очередь | не основное хранилище |
| Объектное хранилище (опц.) | S3/MinIO | аудио, если нужно хранить |

**Почему не другие БД:**

- **SQLite** — отлично для локального dev, но нет pgvector, слабее конкурентность
  и ограничения; для «нормальной реализации» и деплоя — только dev/test.
- **MongoDB** — гибкая схема, но хуже с реляционными ограничениями (пересечения
  встреч, внешние ключи, транзакции); векторный поиск часто vendor lock-in.
- **Qdrant/Weaviate** — хороши при миллионах векторов, но это второй сервис и
  синхронизация данных; для личных задач хватает pgvector.
- **Redis** — не primary DB: нет надёжности и запросов, только кэш/очередь.

### LLM

Основной путь — **дешёвое API с надёжным tool calling**:

- Google Gemini Flash (free tier / дешёвый);
- OpenAI GPT-4o-mini / 4.1-mini;
- DeepSeek Chat;
- Groq (Llama 70B, быстрый inference);
- OpenRouter (free/дешёвые модели, но лимиты).

Абстракция — **LiteLLM** или собственный OpenAI-compatible клиент:

- один интерфейс для всех провайдеров;
- fallback при 429/5xx;
- таймауты, ретраи, учёт токенов;
- возможность локальной модели через Ollama (Qwen2.5 7B/14B, Llama 3.1 8B).

Практика:

- `temperature=0–0.2` для извлечения структуры;
- строгие JSON-схемы инструментов;
- не более 1–2 tool calls на реплику;
- отдельный промпт для классификации «болтовня vs действие»;
- версионирование промптов и golden-set для регрессий.

### STT

| Вариант | Плюсы | Минусы |
|---|---|---|
| **faster-whisper** (`small`/`medium`, int8) | бесплатно, локально, хороший русский | CPU-задержка, RAM |
| **Groq Whisper** | очень быстро, дешёвый/free tier | внешний API |
| **Yandex SpeechKit** | качественный русский, потоковое | платно, зависимость |
| **Vosk** | лёгкий, offline | ниже качество |

Рекомендация: `faster-whisper` + VAD (`silero-vad`) для локального запуска,
Groq — как быстрый fallback для демо.

### TTS

| Вариант | Плюсы | Минусы |
|---|---|---|
| **edge-tts** | бесплатно, хорошие русские голоса | неофициальный сервис |
| **Silero TTS** | локально, русский | качество ниже премиум |
| **Piper** | быстрый локальный | голоса/качество |
| **Yandex SpeechKit / ElevenLabs** | лучшее качество | платно |

Рекомендация: `edge-tts` по умолчанию, Silero — офлайн-fallback, API — если нужен
«вау»-эффект. Всегда оставлять текстовый ответ, если TTS упал.

### Эмбеддинги и поиск

| Задача | Выбор |
|---|---|
| Эмбеддинги (RU) | **BAAI/bge-m3** (1024d), `multilingual-e5-base`, OpenAI `text-embedding-3-small` |
| Rerank | **BAAI/bge-reranker-v2-m3** или Cohere Rerank (опц.) |
| Лексика | PostgreSQL FTS + pg_trgm |
| Слияние | Reciprocal Rank Fusion (RRF) |
| Индекс | HNSW: `m=16`, `ef_construction=64` |

`bge-m3` на CPU может быть тяжёлым по времени и памяти. Fallback —
`intfloat/multilingual-e5-small` или внешний embedding API. Векторный поиск и
rerank включаются флагами `ENABLE_VECTOR_SEARCH` и `ENABLE_RERANK`, чтобы демо
не зависело от тяжёлой части. 

### Frontend

| Задача | Выбор |
|---|---|
| Каркас | React 18/19 + TypeScript + Vite |
| Стили | Tailwind CSS + shadcn/ui |
| Состояние | TanStack Query + Zustand |
| Аудио | MediaRecorder API + wavesurfer.js |
| Стриминг | SSE (проще) или WebSocket |
| Формы | React Hook Form + Zod |
| Тесты | Vitest + Playwright (e2e, опц.) |

Альтернатива: SvelteKit или Next.js. Для SPA с отдельным API Vite проще и
прозрачнее; Next.js оправдан, если нужен SSR/SEO (здесь не нужен).

### Инфраструктура

| Задача | Выбор |
|---|---|
| Контейнеры | Docker + Docker Compose |
| Reverse proxy | Caddy (авто-TLS) или Nginx |
| Хостинг | Fly.io / Render / Railway / VPS |
| Managed Postgres | Neon / Supabase (pgvector поддерживается) |
| CI/CD | GitHub Actions |
| Мониторинг | Sentry + структурные логи; OTel — опционально |
| Секреты | `.env` / secrets хостинга, никогда в git |

---

## 5. Модель данных

### Таблицы

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE event_type AS ENUM ('task', 'meeting', 'reminder');
CREATE TYPE event_status AS ENUM ('planned', 'done', 'cancelled');
CREATE TYPE event_source AS ENUM ('text', 'voice', 'import');

CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         text UNIQUE,
    display_name  text NOT NULL,
    timezone      text NOT NULL DEFAULT 'Europe/Moscow',
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
    recurrence    text,                 -- RRULE, бонус
    parent_id     uuid REFERENCES events(id) ON DELETE SET NULL,
    metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
    search_text   text NOT NULL DEFAULT '',
    tsv           tsvector GENERATED ALWAYS AS
                  (to_tsvector('russian', search_text)) STORED,
    embedding     vector(1024),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    completed_at  timestamptz,
    CONSTRAINT events_time_check CHECK (
        starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at
    ),
    CONSTRAINT events_duration_check CHECK (
        duration_minutes IS NULL OR duration_minutes > 0
    ),
    -- У встречи обязательны начало и конец: открытый конец делает конфликты
    -- неоднозначными. Если пользователь назвал длительность — приложение
    -- вычисляет ends_at = starts_at + duration_minutes.
    CONSTRAINT meetings_time_check CHECK (
        type <> 'meeting' OR (starts_at IS NOT NULL AND ends_at IS NOT NULL)
    )
);

CREATE INDEX events_user_time_idx ON events (user_id, starts_at);
CREATE INDEX events_user_due_idx  ON events (user_id, due_at);
CREATE INDEX events_tsv_idx       ON events USING gin (tsv);
CREATE INDEX events_trgm_idx      ON events USING gin (search_text gin_trgm_ops);
CREATE INDEX events_embedding_idx ON events
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Запрет пересекающихся встреч на уровне БД
ALTER TABLE events ADD CONSTRAINT meetings_no_overlap
EXCLUDE USING gist (
    user_id WITH =,
    tstzrange(starts_at, ends_at, '[)') WITH &&
) WHERE (type = 'meeting' AND status = 'planned' AND starts_at IS NOT NULL);

CREATE TABLE sessions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at    timestamptz NOT NULL DEFAULT now(),
    last_active_at timestamptz NOT NULL DEFAULT now(),
    summary       text,
    metadata      jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE messages (
    id            bigserial PRIMARY KEY,
    session_id    uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role          text NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content       text NOT NULL,
    audio_url     text,
    tool_name     text,
    tool_payload  jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX messages_session_idx ON messages (session_id, created_at);

CREATE TABLE pending_actions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intent        text NOT NULL,          -- create_event / update_event / ...
    slots         jsonb NOT NULL DEFAULT '{}'::jsonb,
    missing       text[] NOT NULL DEFAULT '{}',
    last_entity_id uuid REFERENCES events(id) ON DELETE SET NULL,
    is_active     boolean NOT NULL DEFAULT true,
    expires_at    timestamptz NOT NULL DEFAULT now() + interval '30 minutes',
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX pending_session_idx ON pending_actions (session_id, created_at DESC);

-- В сессии только одно активное уточнение; новое закрывает предыдущее
CREATE UNIQUE INDEX pending_one_active_idx
    ON pending_actions (session_id) WHERE is_active;
```

### Замечания по модели

- `search_text` — нормализованная строка (title + description + леммы) для
  FTS/trigram; заполняется приложением.
- `embedding` — вектор `search_text`; обновляется при создании/изменении.
- Для задач можно использовать `due_at`, для встреч — `starts_at`/`ends_at`.
- Для встреч `ends_at` обязателен (`meetings_time_check`), а `duration_minutes` —
  удобный вход: приложение само считает `ends_at`. Открытый конец встречи
  запрещён, иначе конфликты неоднозначны.
- `pending_actions` — ключ к многошаговому диалогу; хранить слоты и недостающие
  поля, а не только текст сообщений.
- В сессии только одно активное уточнение (partial unique index); новое
  деактивирует предыдущее, чтобы ответы не «подшивались» к чужому действию.
- `last_entity_id` в сессии/действии — для «перенеси её на завтра».
- Все запросы фильтруются по `user_id` из auth-контекста, **никогда** из аргументов
  LLM.

---

## 6. LLM и tool calling

### Инструменты (минимальный набор)

| Инструмент | Назначение |
|---|---|
| `create_event` | создать задачу/встречу/напоминание |
| `update_event` | изменить поля (перенос, переименование) |
| `complete_event` | отметить выполненной |
| `delete_event` | удалить/отменить |
| `list_events` | список за период с фильтрами |
| `search_events` | поиск по смыслу/тексту |
| `ask_clarification` | задать уточняющий вопрос и сохранить pending |
| `get_current_datetime` | текущее время в таймзоне пользователя |

### Пример схемы `create_event`

```json
{
  "name": "create_event",
  "description": "Создать задачу, встречу или напоминание. Не вычисляй даты: верни исходные временные выражения, сервер резолвит их сам.",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["type", "title"],
    "properties": {
      "type": {"enum": ["task", "meeting", "reminder"]},
      "title": {"type": "string", "minLength": 1, "maxLength": 300},
      "description": {"type": ["string", "null"]},
      "time_expression": {
        "type": ["string", "null"],
        "description": "Исходная фраза о времени: 'завтра в 10 утра', 'в пятницу', 'до конца недели'."
      },
      "duration_expression": {
        "type": ["string", "null"],
        "description": "Длительность, если названа: 'на час', '30 минут'."
      },
      "timezone": {"type": "string"},
      "recurrence": {"type": ["string", "null"]},
      "idempotency_key": {"type": "string"}
    }
  }
}
```

`list_events` и `search_events` по той же логике принимают `period_expression`
(`сегодня`, `на этой неделе`) вместо готовых дат; ISO-границы допускаются только
если пользователь назвал их явно.

### Правила

- Аргументы инструментов валидируются Pydantic; при ошибке — вернуть модели
  понятную ошибку, не выполнять действие.
- LLM не заполняет `starts_at`/`ends_at`/`due_at` и не считает даты; она передаёт
  только `time_expression`/`duration_expression`, сервер резолвит их через
  DatetimeParser. Это главный барьер против галлюцинаций.
- `user_id`, `session_id`, `source` подставляются сервером, а не моделью.
- После создания — подтверждение с распознанными полями:
  «Создал задачу: *позвонить Ивану* — завтра, 10:00».
- Никогда не выполнять SQL из текста пользователя.
- Ограничить число tool calls и размер контекста.
- Для «болтовни» — отдельный режим ответа без инструментов.

---

## 7. NLU и работа с датами

### Пайплайн

1. Нормализация текста: числа прописью → цифры, лишние пробелы, пунктуация ASR.
2. LLM: intent + слоты + `time_expression` (исходная фраза), без готовых дат.
3. Серверный DatetimeParser:
   - `dateparser` с `languages=['ru']`, `RELATIVE_BASE=now` в таймзоне пользователя;
   - собственные правила для «до конца недели», «на следующей неделе»,
     «в пятницу», «через два часа»;
   - `time_expression` → `starts_at`/`due_at`, `duration_expression` → `ends_at`;
   - проверка диапазонов и логики (конец ≥ начало);
   - при неоднозначности — уточнение, а не догадка.
4. Если слот обязателен и отсутствует — `ask_clarification`, сохранить
   `pending_action`.
5. Следующая реплика дополняет слоты; после заполнения — выполнение.

### Политика относительных дат

| Фраза | Трактовка |
|---|---|
| `сегодня` | текущая дата, 00:00–23:59 в таймзоне пользователя |
| `завтра` | +1 день |
| `послезавтра` | +2 дня |
| `в пятницу` | ближайшая будущая пятница; если сегодня пятница — уточнить |
| `через два часа` | `now + 2h` с точностью до минуты |
| `на следующей неделе` | пн–вс следующей календарной недели |
| `до конца недели` | дедлайн: воскресенье 23:59, тип — task/reminder |
| `в 10 утра` | 10:00, если дата не указана — уточнить дату |
| `утром` / `днём` / `вечером` / `ночью` | дефолт 09:00 / 13:00 / 18:00 / 22:00 и подтверждение («Поставил на 18:00, изменить?») |
| дата есть, времени нет | уточнить время или предложить дефолт с подтверждением |

Все даты хранить в UTC (`timestamptz`), отображать в таймзоне пользователя.

### Пример

```
Пользователь: «Напомни мне завтра в 10 утра позвонить Ивану»
LLM: create_event(type=reminder, title="Позвонить Ивану",
                  time_expression="завтра в 10 утра")
Сервер: dateparser → due_at=<tomorrow 10:00>, валидация, сохранение
Ответ: «Напоминание создано: завтра в 10:00 — позвонить Ивану»
```

---

## 8. Поиск по старым задачам

### Порядок внедрения

1. Обычный текстовый поиск по `title`/`description`.
2. PostgreSQL FTS `russian`.
3. `pg_trgm` для опечаток и падежей.
4. Расширение запроса LLM (ключевые слова/синонимы) для лексики.
5. Векторный поиск — флаг `ENABLE_VECTOR_SEARCH`.
6. RRF и rerank — флаг `ENABLE_RERANK`.

Ядро должно работать на шагах 1–3 даже при отключённых векторах. Если вектор
отключён или модель недоступна — честно указать это в README и продолжить
лексическим поиском.

### Гибридная схема

1. **Лексический поиск**
   - FTS `russian` по `search_text` (леммы);
   - `pg_trgm` similarity для опечаток и падежей;
   - расширение запроса: LLM вытаскивает 3–5 ключевых слов и синонимов;
   - учитывать фильтры: тип, диапазон дат, статус.

2. **Семантический поиск** (если включён флагом)
   - embedding запроса (bge-m3 / e5-small / API);
   - pgvector cosine top-K (например, 30);
   - порог отсечения + fallback на лексику.

3. **Слияние**
   - Reciprocal Rank Fusion: `score = Σ 1/(k + rank)`, `k=60`;
   - опционально rerank top-10 моделью `bge-reranker-v2-m3`.

4. **Ответ**
   - top-5 с датой, типом и сниппетом;
   - если пусто — честно сказать и предложить изменить формулировку;
   - не выдавать выдуманные записи.

### Feature flags

| Флаг | Что отключает | Зачем |
|---|---|---|
| `ENABLE_VECTOR_SEARCH=false` | векторный этап | демо не падает без тяжёлой модели |
| `ENABLE_RERANK=false` | reranker | экономия ресурсов |
| `EMBEDDINGS_PROVIDER=local\|api\|off` | выбор источника эмбеддингов | bge-m3, e5-small или внешний API |

### Индексация

- эмбеддинг считается при создании/изменении события (синхронно или через
  `BackgroundTasks`; ARQ — только если уже есть worker);
- backfill-скрипт для импорта;
- хранить `embedding_model` в metadata, чтобы понимать версию;
- при смене модели — переиндексация.

### Датасет из задания

`voice_assistant_events_1000_*.csv`:

- 1000 строк, 376 уникальных текстов (624 дубля);
- даты 2024–2027, время 08:00–20:00;
- UTF-8 BOM, колонки `id,date,time,text`;
- текст с падежными ошибками («Отправить договор Иваном»), поэтому точный поиск
  заведомо плох.

Использовать как:

1. seed-корпус для демо и проверки поиска;
2. основу для golden-set: вручную составить 50–100 запросов и ожидаемые записи;
3. проверить дедупликацию и классификацию типов.

Импорт: скрипт читает CSV, классифицирует тип по ключевым словам
(`встреча/созвон/планёрка/демо` → meeting, `напомнить` → reminder, иначе task),
нормализует текст, опционально дедуплицирует по `(title, date, time)`.

---

## 9. Контекст диалога

Хранить три уровня:

1. **Сообщения** — `messages` (роль, текст, tool payload, timestamp).
2. **Состояние сессии** — `pending_action` (intent, слоты, missing,
   `last_entity_id`), таймзона, активный диапазон дат.
3. **Долгосрочная память** — summary старых сессий + семантический поиск по
   сообщениям (опционально).

Правила:

- В промпт идут: system + summary + последние 8–12 сообщений + результаты
  инструментов. Старое сжимается в summary.
- «её/его/это» разрешается через `last_entity_id`; если неоднозначно — уточнить.
- «А какие там планы?» — «там» = последняя упомянутая дата/тема; если непонятно,
  задать вопрос.
- Контекст диалога **не заменяет** запрос к БД: «что у меня завтра» всегда
  выборка по датам.
- В сессии не более одного активного `pending_action`; новое уточнение
  деактивирует предыдущее, иначе ответ пользователя попадёт не в то действие.
- Срок жизни `pending_action` — 15–30 минут; потом сбрасывать.
- Мультипользовательность: все ключи контекста привязаны к `user_id`.

---

## 10. API (черновик)

```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout

POST   /api/v1/chat                 # текст → ответ (JSON или SSE)
POST   /api/v1/voice                # multipart audio → transcript + ответ
GET    /api/v1/chat/stream          # SSE-стриминг ответа (опц.)

GET    /api/v1/events?from&to&type&status
POST   /api/v1/events
PATCH  /api/v1/events/{id}
POST   /api/v1/events/{id}/complete
DELETE /api/v1/events/{id}

POST   /api/v1/search               # {query, filters}

GET    /api/v1/sessions/{id}/messages
POST   /api/v1/clarifications/{id}/answer

GET    /healthz
GET    /readyz
GET    /metrics                     # опц.
```

Ответ чата:

```json
{
  "session_id": "...",
  "reply": "Создал задачу: позвонить Ивану — завтра в 10:00",
  "action": {
    "name": "create_event",
    "status": "done",
    "entity_id": "..."
  },
  "audio_url": "/api/v1/audio/...",
  "clarification": null
}
```

---

## 11. UX-идеи

- Push-to-talk: большая кнопка, запись, отмена, таймер.
- Показ промежуточной расшифровки; возможность отредактировать текст до отправки.
- Карточка распознанного действия: `Задача · завтра 10:00 · Позвонить Ивану` с
  кнопками «Изменить» / «Отменить».
- Уточнения — быстрые варианты ответа («Сегодня», «Завтра», «Выбрать дату»).
- Лента «Сегодня / Завтра / Неделя» с группировкой по времени.
- Поиск с подсветкой совпадений и фильтрами (тип, период).
- Предупреждение о конфликте встреч с предложением перенести.
- TTS-переключатель и кнопка «повторить».
- Undo после создания/удаления.
- Мобильная вёрстка, клавиатурные шорткаты, доступность.
- Демо-режим с импортированным CSV и готовыми примерами запросов.

---

## 12. «Нормальная реализация», а не MVP

### Ядро (обязательно для сдачи)

- чистая архитектура и DI, без бизнес-логики в роутерах;
- миграции Alembic, индексы, CHECK/EXCLUDE-ограничения, транзакции;
- demo-user + изоляция данных по `user_id` (полный auth — позже);
- таймауты, ретраи, fallback LLM;
- Pydantic-валидация всех tool-аргументов;
- structured logging и request_id;
- тесты: unit (даты, слоты), integration (БД через testcontainers),
  e2e (создание → список → поиск), golden-set NLU;
- CI: ruff, mypy, pytest, сборка Docker;
- Docker Compose: api, postgres, frontend (Redis/worker — опционально);
- healthchecks;
- README с архитектурой, решениями, trade-offs и планом улучшений;
- seed-скрипт и demo-данные.

### Production-hardening (после ядра)

- полный auth, rate limit, разграничение ролей;
- Redis/ARQ — только если реально доставляются напоминания;
- Sentry/OTel, метрики, backup-стратегия;
- версионирование промптов и автоматическая оценка регрессий;
- политика хранения аудио (удалять после распознавания или хранить N дней);
- graceful shutdown и нагрузочное тестирование.

Не делать:

- SQL-строки из LLM;
- хранение задач только в памяти/сессии LLM;
- «магические» регулярки на все случаи без тестов;
- один гигантский промпт на всё;
- доверие к датам от LLM без проверки;
- старт с Redis/ARQ/полного auth/мониторинга до стабильных 4 сценариев;
- секреты в репозитории.

---

## 13. Библиотеки: сводка

| Область | Библиотека | Зачем |
|---|---|---|
| API | `fastapi`, `uvicorn` | HTTP, OpenAPI, SSE |
| Схемы | `pydantic`, `pydantic-settings` | валидация, настройки |
| ORM | `sqlalchemy[asyncio]`, `asyncpg`, `alembic` | БД, миграции |
| Векторы | `pgvector` (Python) | тип и операции |
| LLM | `litellm`, `openai` | провайдеры, tool calling |
| STT | `faster-whisper`, `silero-vad` | локальное распознавание |
| TTS | `edge-tts`, `silero` | синтез |
| Даты | `dateparser` | русские относительные даты |
| Морфология | `pymorphy3`, `natasha` | леммы, имена |
| Нечёткий текст | `rapidfuzz` | similarity, дедупликация |
| Эмбеддинги | `sentence-transformers`, `FlagEmbedding` | bge-m3, reranker |
| Планировщик | `arq` (опц.) / `apscheduler` | напоминания; на старте не обязателен |
| Логи | `structlog` | JSON-логи |
| Тесты | `pytest`, `pytest-asyncio`, `httpx`, `testcontainers`, `respx` | unit/integration |
| Качество | `ruff`, `mypy`, `pre-commit` | стиль и типы |
| Frontend | `react`, `typescript`, `vite`, `tailwindcss`, `@tanstack/react-query`, `zustand`, `wavesurfer.js` | UI и аудио |
| E2E | `playwright` | сквозные сценарии |

---

## 14. Этапы работ

| Этап | Результат |
|---|---|
| 0. Каркас | репозиторий, Docker Compose (api + postgres + frontend), FastAPI, React, миграции |
| 1. Домен | CRUD событий, список за период, demo-user, seed CSV |
| 2. NLU | LLM tool calling, `time_expression`, DatetimeParser, `pending_actions`, уточнения |
| 3. Поиск | текст → FTS → trigram → (флаг) vector/RRF/rerank, golden-set |
| 4. Голос | запись, STT, TTS, обязательный текстовый fallback |
| 5. Бонусы | update/delete/complete, конфликты, recurring, напоминания |
| 6. Полировка | тесты, CI, деплой, README, demo-ссылка; инфраструктура по необходимости |

---

## 15. Риски и mitigation

| Риск | Что делать |
|---|---|
| Плохое качество русского STT | faster-whisper medium / Groq, VAD, показ расшифровки для правки |
| Лимиты бесплатных LLM | fallback-провайдер, retries, кэш ответов, локальная модель |
| LLM придумывает даты | `time_expression` + серверный DatetimeParser; ISO-даты от модели не принимаются |
| Неоднозначные фразы | `pending_action` + явный вопрос |
| Несколько активных уточнений | partial unique index + деактивация предыдущего |
| Тяжёлые локальные эмбеддинги | флаг vector, e5-small/API fallback |
| Долгий ответ | стриминг текста, TTS после первого предложения |
| Конфликты встреч | EXCLUDE-ограничение + понятное сообщение |
| Деплой аудио | ограничение размера, временные файлы, S3 при необходимости |
| Приватность | не логировать содержимое аудио, retention policy, ключи в secrets |

---

## 16. Что написать в README

1. Что это и какие сценарии работают.
2. Быстрый запуск: `.env`, `docker compose up`, миграции, seed.
3. Архитектура и схема потоков (голос → STT → LLM → tools → БД → TTS).
4. Выбранные технологии и почему — не список, а «решение → причина»:
   FastAPI (async, Pydantic, tool calling), PostgreSQL (транзакции, FTS,
   trigram, EXCLUDE), pgvector (без отдельной vector DB), LiteLLM (fallback
   провайдеров), dateparser (даты), `pending_actions` (уточнения).
5. Как устроен контекст и уточнения.
6. Как работает поиск (FTS + trigram, опционально vector/RRF/rerank) и какие
   флаги что включают.
7. Ограничения и что улучшил бы:
   - интеграция с Google Calendar/CalDAV;
   - повторяющиеся события и полноценный планировщик;
   - мультиустройство и push-уведомления;
   - улучшение ASR на именах/доменах;
   - A/B промптов и автоматическая оценка качества.
8. Ссылка на демо и тестовые аккаунты.

---

## 17. Что подчеркнуть на демо и в README

1. LLM — оркестратор, а не хранилище данных.
2. Все действия выполняются через типизированные инструменты с Pydantic-валидацией.
3. Даты считает сервер, а не модель.
4. Все 4 обязательных сценария стабильны.
5. Свободные формулировки и синонимы, а не жёсткие команды.
6. Уточняющие вопросы при недостающих данных.
7. Данные сохраняются между запросами.
8. Поиск работает не только по точному совпадению.
9. Конфликты встреч контролируются на уровне БД.
10. Архитектура разделяет API, бизнес-логику, LLM, поиск и хранение.

---

## 18. Полезные ссылки

- FastAPI — https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 — https://docs.sqlalchemy.org/en/20/
- Alembic — https://alembic.sqlalchemy.org/
- PostgreSQL FTS — https://www.postgresql.org/docs/current/textsearch.html
- pgvector — https://github.com/pgvector/pgvector
- pg_trgm — https://www.postgresql.org/docs/current/pgtrgm.html
- LiteLLM — https://docs.litellm.ai/
- faster-whisper — https://github.com/SYSTRAN/faster-whisper
- dateparser — https://dateparser.readthedocs.io/
- BGE-M3 — https://huggingface.co/BAAI/bge-m3
- edge-tts — https://github.com/rany2/edge-tts
- ARQ — https://arq-docs.helpmanual.io/
- React — https://react.dev/
- Vite — https://vite.dev/
