# План реализации: голосовой ассистент для задач и встреч

> Документ-основа для тестового задания. База проекта — **OpenClaw**: он отвечает
> за каналы, сессии, память, голос и планировщик; наш слой — плагин задач и встреч.
> Здесь: краткий разбор задания, архитектура, стек, модель данных, идеи по
> NLU/поиску/контексту, библиотеки, этапы работ и приоритеты: сначала стабильное
> ядро из 4 сценариев, затем контекст, поиск, голос и только потом инфраструктура
> и бонусы.

---

## 1. Задание кратко

### Цель

Прототип голосового ассистента, который помогает управлять личными задачами,
напоминаниями и встречами. Пользователь обращается голосом или текстом в свободной
форме и получает текстовый или голосовой ответ. Главный акцент — **логика
ассистента**, а не интерфейс: понимание запроса, работа с данными, корректное
выполнение действий. Интерфейс не пишем с нуля: его даёт OpenClaw (Telegram,
WebChat/Control UI и другие каналы).

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
Диалоговую историю, сессии и память хранит OpenClaw; доменные записи — в PostgreSQL
(см. §5).

### Голосовой интерфейс

Минимальный цикл:

```
голос → OpenClaw STT → агент + skill → tool → действие → ответ (TTS или текст)
```

Разрешены готовые API и библиотеки для STT, TTS и LLM. Интерфейс может быть
минимальным: кнопка записи, история диалога, ответ ассистента. В OpenClaw это
встроено: после включения аудио голосовые заметки в Telegram/WhatsApp
распознаются, ответ можно озвучить через TTS. Наш плагин не занимается аудио.

### Что сдать

1. Ссылка на репозиторий с исходным кодом: плагин OpenClaw, skill, миграции,
   seed и конфиги.
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
2. Уточняющий диалог и контекст через `pending_actions` + OpenClaw-сессию.
3. Поиск: сначала FTS + trigram, затем (по флагу) векторный.
4. Голос: встроенные STT/TTS OpenClaw + обязательный текстовый fallback.
5. Бонусы и инфраструктура (свой scheduler, Redis, полный auth, мониторинг) —
   только после стабильного ядра.

---

## 2. Ключевая идея решения

**OpenClaw — агентская основа, LLM понимает и вызывает инструменты, PostgreSQL хранит правду, плагин валидирует.**

OpenClaw даёт то, что не относится к предметной логике: подключение каналов
(Telegram, WebChat/Control UI, WhatsApp и др.), сессии и память, доступ к моделям
с fallback, распознавание голосовых заметок, TTS и планировщик напоминаний.
Второй агентский runtime не строим и не дублируем `sessions`/`messages`.
Наш слой — плагин `openclaw-tasks`: инструменты, skill, доменные правила и БД.

Нельзя строить ассистента так, чтобы модель «помнила» задачи или придумывала даты.
Правильный контур:

```
текст/голос (Telegram, WebChat, ...)
   ↓
OpenClaw Gateway: канал → STT (если голос) → сессия/память → LLM
   ↓
skill + tool call (строгая TypeBox-схема)
   ↓
плагин: валидация + серверный DatetimeParser
   ↓
доменный сервис → PostgreSQL
   ↓
ответ → канал / TTS
```

Ключевые принципы:

1. **OpenClaw — транспорт и память, не хранилище задач.** Сессии, транскрипты и
   память живут в OpenClaw; задачи/встречи — только в доменной БД.
2. **LLM — оркестратор, а не хранилище.** Все задачи/встречи читаются и пишутся
   только через инструменты и БД.
3. **Гибридный NLU.** LLM извлекает intent, тип, название и исходное временное
   выражение (`time_expression`); `chrono-node`/правила резолвят даты на сервере,
   TypeBox проверяет аргументы. Модель не возвращает готовые ISO-даты как истину.
4. **Даты резолвит сервер.** `time_expression` → конкретные `starts_at`/`due_at`
   в таймзоне пользователя; при неоднозначности — уточняющий вопрос.
5. **Структурированный контекст.** OpenClaw хранит транскрипт и память, а плагин —
   `pending_action` (ключ — `sessionKey`), незаполненные слоты, `last_entity_id`,
   таймзону.
6. **Уточнение вместо выдумывания.** Не хватает времени/даты — задать вопрос и
   сохранить незавершённое намерение.
7. **Гибридный поиск.** Сначала лексика (FTS + trigram), затем по флагу векторный
   поиск и rerank. Поиск только на embeddings на коротких русских фразах
   работает нестабильно.
8. **Деградация без LLM.** OpenClaw умеет fallback между моделями; при полной
   недоступности — понятная ошибка и повтор, а не выдуманные данные. Даты и
   валидация при этом остаются детерминированными.

---

## 3. Архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│  Каналы OpenClaw: Telegram, WebChat/Control UI, WhatsApp, ...     │
│  текст и голосовые заметки                                        │
└───────────────┬──────────────────────────────────────────────────┘
                │ Gateway WebSocket / channel adapters
┌───────────────▼──────────────────────────────────────────────────┐
│  OpenClaw Gateway — основа проекта                                │
│  ├── sessions / memory / compaction                               │
│  ├── model providers + fallback                                   │
│  ├── STT голосовых заметок и TTS                                  │
│  ├── automations — напоминания и фоновые запуски                  │
│  └── skills + plugin runtime                                      │
├──────────────────────────────────────────────────────────────────┤
│  Наш плагин: openclaw-tasks                                       │
│  ├── tools: create/update/complete/delete/list/search             │
│  ├── skill: правила дат, уточнений и ответов                      │
│  ├── domain services + DatetimeParser                             │
│  └── pending actions + привязка OpenClaw identity                 │
├──────────────────────────────────────────────────────────────────┤
│  Integrations                                                     │
│  ├── PostgreSQL (pg + миграции)                                   │
│  ├── Embeddings (API/Ollama, опционально)                         │
│  └── OpenClaw automations (one-shot reminders)                    │
└───────────────┬──────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────┐
│  PostgreSQL 16+                                                   │
│  ├── pgvector       — эмбеддинги событий                          │
│  ├── pg_trgm        — нечёткий лексический поиск                  │
│  ├── FTS russian    — полнотекстовый поиск                        │
│  ├── btree_gist     — запрет пересечения встреч                   │
│  └── JSONB          — слоты, метаданные, состояние диалога        │
└──────────────────────────────────────────────────────────────────┘
```

### Разделение слоёв

| Слой | Ответственность | Не должен знать |
|---|---|---|
| `plugin/` | manifest, tools, config, hooks | про SQL-детали и промпты |
| `skills/` | `SKILL.md`: когда и как вызывать tools | про HTTP и БД |
| `services/` | бизнес-правила, сценарии | про OpenClaw SDK и ORM-детали |
| `repositories/` | доступ к БД | про LLM |
| `integrations/` | embeddings, automations, внешние API | про доменные правила |
| `db/` | SQL-миграции и схема | про агентский runtime |
| `schemas/` | TypeBox-схемы tool-аргументов | про БД |

---

## 4. Рекомендуемый стек

### Основа и плагин

| Задача | Выбор | Почему |
|---|---|---|
| Основа | **OpenClaw Gateway** | каналы, сессии, память, голос, планировщик из коробки |
| Runtime | Node.js 24.16+ / 26.1+ | требование OpenClaw; один язык с плагином |
| Плагин | TypeScript ESM + OpenClaw Plugin SDK | типизированные tools и lifecycle |
| Схемы | TypeBox | те же схемы для tool calling и валидации |
| БД | PostgreSQL 16/17 | FTS, trigram, pgvector, EXCLUDE |
| Драйвер | `pg` | зрелый async-драйвер |
| ORM/запросы | Drizzle ORM + drizzle-kit | типизация и миграции |
| Настройки | configSchema плагина + `.env` | секреты не в коде |
| Логи | `api.logger` | структурные JSON-логи, session key |
| Фон | OpenClaw automations; plugin service для backfill | не нужен свой worker |
| Тесты | Vitest + testcontainers + `openclaw agent` | unit/integration/e2e |
| Качество | `tsc`, `oxlint`, `prettier`, pre-commit | типы, линт, формат |
| CI | GitHub Actions | тесты, линт, сборка плагина |

> На этапе ядра не нужны свой scheduler, Redis, отдельный фронтенд и полный auth:
> demo-user, OpenClaw automations, Control UI. Инфраструктура — после стабильных
> 4 сценариев.

### Данные

| Компонент | Выбор | Комментарий |
|---|---|---|
| Основная БД | **PostgreSQL 16/17** | реляционная модель + ограничения целостности |
| Состояние OpenClaw | **SQLite + workspace** (по умолчанию) | сессии/транскрипты в SQLite, память — Markdown; не дублировать |
| Векторы | **pgvector** (HNSW, cosine) | не нужен отдельный vector DB |
| Нечёткий поиск | **pg_trgm** | опечатки, падежи, короткие фразы |
| Полнотекст | **FTS `russian`** | точные слова, ранжирование |
| Пересечения встреч | **btree_gist + EXCLUDE** | конфликт на уровне БД, а не в коде |
| JSONB | слоты и метаданные | гибкость без потери схемы |
| Redis (опц.) | кэш, rate limit | в ядре не используется, только при реальной нагрузке |
| Объектное хранилище (опц.) | S3/MinIO | аудио, если нужно хранить дольше OpenClaw |

**Почему не другие БД:**

- **SQLite** — родная БД OpenClaw для сессий и служебного состояния, хороша для
  локального dev; для домена не берём: нет pgvector/EXCLUDE и слабее
  конкурентность. Состояние OpenClaw при этом остаётся в SQLite.
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

Абстракция — **OpenClaw model providers**:

- один интерфейс для всех провайдеров (`models.providers`);
- fallback-цепочка при 429/5xx и таймаутах;
- выбор модели командой `/model`, лимиты и учёт токенов;
- локальная модель через Ollama (Qwen2.5 7B/14B, Llama 3.1 8B).

Практика:

- `temperature=0–0.2` для извлечения структуры (если провайдер поддерживает);
- строгие TypeBox-схемы инструментов;
- не более 1–2 tool calls на реплику;
- отдельный skill/инструкция для «болтовня vs действие»;
- версионирование `SKILL.md` и golden-set для регрессий.

### STT

OpenClaw умеет принимать голосовые заметки; от нас — только включить аудио и
выбрать провайдера распознавания.

| Вариант | Плюсы | Минусы |
|---|---|---|
| **OpenClaw: Groq/OpenAI/Deepgram** | штатно, быстро, без своего кода | внешний API |
| **OpenClaw: локальные CLI** (`whisper-cli`, `whisper`, `sherpa-onnx`) | бесплатно, локально, хороший русский | CPU-задержка, RAM |
| **Yandex SpeechKit** | качественный русский, потоковое | нужен свой адаптер/CLI, платно |
| **Vosk** | лёгкий, offline | нужен свой адаптер, ниже качество |

Рекомендация: OpenClaw STT через Groq/OpenAI для демо, локальный `whisper-cli`
как fallback; включить `echoTranscript`, чтобы пользователь видел расшифровку
и мог её поправить.

### TTS

TTS — встроенный инструмент OpenClaw (`tts`); можно отвечать голосом прямо
в Telegram/WhatsApp.

| Вариант | Плюсы | Минусы |
|---|---|---|
| **OpenClaw: Microsoft edge (без ключа)** | штатно, бесплатно, хорошие русские голоса | неофициальный сервис |
| **OpenClaw: OpenAI / ElevenLabs** | штатно, лучшее качество | платно |
| **Silero / Piper (local CLI)** | локально, русский | нужен CLI/адаптер, качество/настройка |
| **Yandex SpeechKit** | качественный русский | нужен адаптер, платно |

Рекомендация: OpenClaw TTS через edge по умолчанию, API — если нужен «вау»-эффект.
Всегда оставлять текстовый ответ, если TTS упал.

### Эмбеддинги и поиск

| Задача | Выбор |
|---|---|
| Эмбеддинги (RU) | **BAAI/bge-m3** через Ollama/API (1024d) или OpenAI `text-embedding-3-small` с `dimensions=1024` |
| Rerank | **BAAI/bge-reranker-v2-m3** или Cohere Rerank (опц.) |
| Лексика | PostgreSQL FTS + pg_trgm |
| Слияние | Reciprocal Rank Fusion (RRF) |
| Индекс | HNSW: `m=16`, `ef_construction=64` |

`bge-m3` на CPU может быть тяжёлым по времени и памяти. Fallback — внешний
embedding API с 1024d; другая размерность требует отдельной колонки и
переиндексации. Векторный поиск и rerank включаются флагами
`ENABLE_VECTOR_SEARCH` и `ENABLE_RERANK`, чтобы демо не зависело от тяжёлой части.

### Интерфейс

| Задача | Выбор |
|---|---|
| Основной канал | Telegram: текст + голосовые заметки |
| Desktop | OpenClaw Control UI / WebChat |
| Другие каналы | WhatsApp, Discord, Slack — без отдельного кода |
| Стриминг | встроенный в OpenClaw |
| Расширение UI | опционально plugin panel в Control UI |
| Тесты | сценарии через `openclaw agent` + ручная проверка |

Свой React-фронтенд не нужен: каналы, история, стриминг и голос уже есть в
OpenClaw. Кастомный UI оправдан только для админки/отладки и не входит в ядро.

### Инфраструктура

| Задача | Выбор |
|---|---|
| Контейнеры | Docker + Docker Compose (OpenClaw Gateway + PostgreSQL) |
| Установка | установщик/npm OpenClaw + `openclaw onboard` или контейнер |
| Reverse proxy | Caddy/Nginx только для удалённого Gateway; Tailscale/SSH предпочтительнее |
| Хостинг | VPS / Fly.io / Render |
| Managed Postgres | Neon / Supabase (pgvector поддерживается) |
| CI/CD | GitHub Actions |
| Мониторинг | OpenClaw logs/doctor + Sentry; OTel — опционально |
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
    openclaw_peer_id text UNIQUE,       -- trusted sender id из OpenClaw (channel:sender)
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

-- Сессии, транскрипты и память хранит OpenClaw; в доменной БД их не дублируем.

CREATE TABLE pending_actions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key   text NOT NULL,          -- OpenClaw session key
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

CREATE INDEX pending_session_idx ON pending_actions (session_key, created_at DESC);

-- В сессии только одно активное уточнение; новое закрывает предыдущее
CREATE UNIQUE INDEX pending_one_active_idx
    ON pending_actions (session_key) WHERE is_active;
```

### Замечания по модели

- `search_text` — нормализованная строка (title + description + синонимы) для
  FTS/trigram; лемматизацию для FTS делает PostgreSQL, приложение только
  поддерживает строку в актуальном виде.
- `embedding` — вектор `search_text`; обновляется при создании/изменении.
- Для задач можно использовать `due_at`, для встреч — `starts_at`/`ends_at`.
- Для встреч `ends_at` обязателен (`meetings_time_check`), а `duration_minutes` —
  удобный вход: приложение само считает `ends_at`. Открытый конец встречи
  запрещён, иначе конфликты неоднозначны.
- `pending_actions` — ключ к многошаговому диалогу; хранить слоты и недостающие
  поля, а не только текст сообщений. Ключ — `session_key` из OpenClaw, а не
  собственная таблица сессий.
- В сессии только одно активное уточнение (partial unique index); новое
  деактивирует предыдущее, чтобы ответы не «подшивались» к чужому действию.
- `last_entity_id` в действии — для «перенеси её на завтра».
- `openclaw_peer_id` связывает пользователя с trusted-отправителем OpenClaw;
  все запросы фильтруются по `user_id`, полученному из контекста OpenClaw,
  **никогда** из аргументов LLM.
- В демо неизвестный peer маппится на demo-user или автосоздаётся; в production —
  только после pairing/allowlist.
- Сессии, сообщения и память OpenClaw не дублируются в PostgreSQL; источник
  истины для диалога — OpenClaw, для задач/встреч — доменная БД.
- Для напоминаний id созданной automation хранится в `events.metadata`.

---

## 6. LLM и tool calling

### Инструменты (минимальный набор)

| Инструмент | Источник | Назначение |
|---|---|---|
| `create_event` | плагин | создать задачу/встречу/напоминание |
| `update_event` | плагин | изменить поля (перенос, переименование) |
| `complete_event` | плагин | отметить выполненной |
| `delete_event` | плагин | удалить/отменить |
| `list_events` | плагин | список за период с фильтрами |
| `search_events` | плагин | поиск по смыслу/тексту |
| `ask_user` | OpenClaw | уточняющий вопрос с вариантами ответа |
| `get_current_datetime` | плагин | текущее время в таймзоне пользователя |

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
      "recurrence": {"type": ["string", "null"]},
      "idempotency_key": {"type": "string"}
    }
  }
}
```

`list_events` и `search_events` по той же логике принимают `period_expression`
(`сегодня`, `на этой неделе`) вместо готовых дат; ISO-границы допускаются только
если пользователь назвал их явно.

Для `reminder` (и опционально для task/meeting с `due_at`/`starts_at`)
`create_event` создаёт one-shot automation с доставкой в текущую сессию/канал
через plugin service (`ctx.getCron()`); id job сохраняется в `metadata`, чтобы
напоминание можно было перенести или отменить.

### Правила

- Аргументы инструментов валидируются TypeBox (схему проверяет и OpenClaw до
  вызова); при ошибке — вернуть модели понятную ошибку, не выполнять действие.
- LLM не заполняет `starts_at`/`ends_at`/`due_at` и не считает даты; она передаёт
  только `time_expression`/`duration_expression`, сервер резолвит их через
  DatetimeParser. Это главный барьер против галлюцинаций.
- `user_id`, `session_key` подставляются плагином из trusted-контекста
  OpenClaw (`requesterSenderId`/сессия), а `source` определяется по входному
  сообщению (текст/голос/импорт), а не моделью.
- Таймзона берётся из `users.timezone`/OpenClaw, а не из аргументов; явно
  названная зона («по Лондону») разбирается сервером в `time_expression`.
- После создания — подтверждение с распознанными полями:
  «Создал задачу: *позвонить Ивану* — завтра, 10:00».
- Никогда не выполнять SQL из текста пользователя.
- Ограничить число tool calls и размер контекста.
- Для «болтовни» — отдельный режим ответа без инструментов.
- Если слот отсутствует, skill вызывает `create_event`/`update_event` с
  частичными слотами: инструмент сохраняет `pending_action` и возвращает
  `needs_clarification`; затем агент задаёт вопрос (`ask_user` или текст).
  Следующая реплика дополняет слоты.
- Возвращать короткий текст для пользователя и структурированные `details` для
  тестов/UI; не отдавать модели лишние поля.

---

## 7. NLU и работа с датами

### Пайплайн

1. Нормализация текста: числа прописью → цифры, лишние пробелы, пунктуация ASR.
2. OpenClaw agent + skill: intent + слоты + `time_expression` (исходная фраза),
   без готовых дат.
3. Серверный DatetimeParser:
   - `chrono-node` с локалью `ru` и `referenceDate=now` в таймзоне пользователя;
   - `luxon` для границ дня/недели и перевода в UTC;
   - собственные правила для «до конца недели», «на следующей неделе»,
     «в пятницу», «через два часа»;
   - `time_expression` → `starts_at`/`due_at`, `duration_expression` → `ends_at`;
   - проверка диапазонов и логики (конец ≥ начало);
   - при неоднозначности — уточнение, а не догадка.
4. Если слот обязателен и отсутствует — инструмент сохраняет `pending_action`
   с `session_key`, агент задаёт вопрос (`ask_user` или текст).
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
OpenClaw: skill → create_event(type=reminder, title="Позвонить Ивану",
                             time_expression="завтра в 10 утра")
Плагин: chrono-node → due_at=<tomorrow 10:00>, валидация, сохранение
Ответ: «Напоминание создано: завтра в 10:00 — позвонить Ивану»
```

---

## 8. Поиск по старым задачам

`memory_search` OpenClaw ищет по памяти и заметкам, а не по задачам;
для событий используется только доменная БД.

### Порядок внедрения

1. Обычный текстовый поиск по `title`/`description`.
2. PostgreSQL FTS `russian`.
3. `pg_trgm` для опечаток и падежей.
4. Расширение запроса через skill/LLM (ключевые слова/синонимы) для лексики.
5. Векторный поиск — флаг `ENABLE_VECTOR_SEARCH`.
6. RRF и rerank — флаг `ENABLE_RERANK`.

Ядро должно работать на шагах 1–3 даже при отключённых векторах. Если вектор
отключён или модель недоступна — честно указать это в README и продолжить
лексическим поиском.

### Гибридная схема

1. **Лексический поиск**
   - FTS `russian` по `search_text` (леммы);
   - `pg_trgm` similarity для опечаток и падежей;
   - расширение запроса: skill/LLM вытаскивает 3–5 ключевых слов и синонимов;
   - учитывать фильтры: тип, диапазон дат, статус.

2. **Семантический поиск** (если включён флагом)
   - embedding запроса (bge-m3 / API 1024d);
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
| `EMBEDDINGS_PROVIDER=local\|api\|off` | выбор источника эмбеддингов | Ollama/bge-m3, внешний API или отключено |

### Индексация

- эмбеддинг считается при создании/изменении события (синхронно или через
  plugin service; отдельный worker не нужен);
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

Контекст делим на два уровня, чтобы не дублировать OpenClaw:

1. **Диалог** — сессия, транскрипт, summary и память OpenClaw. Это источник
   истины для «что я говорил»; плагин их не копирует.
2. **Доменное состояние** — `pending_action` (intent, слоты, missing,
   `last_entity_id`) в PostgreSQL, ключ — OpenClaw `sessionKey`, плюс таймзона.

Правила:

- В промпт OpenClaw сам подставляет system, память и последние сообщения;
  плагин добавляет только результат инструментов и `pending_action`.
- «её/его/это» разрешается через `last_entity_id`; если неоднозначно — уточнить.
- «А какие там планы?» — «там» = последняя упомянутая дата/тема; если непонятно,
  задать вопрос.
- Контекст диалога **не заменяет** запрос к БД: «что у меня завтра» всегда
  выборка по датам.
- В сессии не более одного активного `pending_action`; новое уточнение
  деактивирует предыдущее, иначе ответ пользователя попадёт не в то действие.
- Срок жизни `pending_action` — 15–30 минут; потом сбрасывать.
- Мультипользовательность: `openclaw_peer_id` → `user_id`; все ключи контекста
  привязаны к `user_id`, а `sessionKey` изолирует диалоги.
- Для групп/нескольких устройств использовать OpenClaw `dmScope`/identity links,
  а не собственную логику склейки.

---

## 10. Интерфейсы

Отдельного HTTP API для чата нет: вход — каналы OpenClaw, выход — его ответы.
Плагин регистрирует инструменты, которые вызывает агент; снаружи работа идёт
через Gateway RPC/CLI (turn агента), а не через собственный HTTP API.

```
openclaw gateway
openclaw agent --message "Что у меня завтра?"
openclaw plugins inspect openclaw-tasks --runtime

openclaw automations list
openclaw automations runs <job-id>
```

Контракт инструмента (упрощённо):

```json
{
  "tool": "create_event",
  "status": "done",
  "entity": {
    "id": "...",
    "type": "task",
    "title": "Позвонить Ивану",
    "due_at": "2026-10-23T10:00:00+03:00"
  },
  "reply": "Создал задачу: позвонить Ивану — завтра в 10:00",
  "clarification": null
}
```

Опционально плагин может зарегистрировать HTTP healthcheck; чат и CRUD наружу
не выставляются.

---

## 11. UX-идеи

- Push-to-talk: в Telegram — голосовая заметка; в Control UI/нативных приложениях —
  Talk/push-to-talk OpenClaw.
- Показ расшифровки (`echoTranscript`) и возможность исправить текст до отправки.
- Карточка действия: `Задача · завтра 10:00 · Позвонить Ивану` со
  структурированными `details`; кнопки «Изменить» / «Отменить» — follow-up
  сообщением.
- Уточнения — через `ask_user` с быстрыми вариантами («Сегодня», «Завтра»,
  «Выбрать дату»).
- Лента «Сегодня / Завтра / Неделя» — группировка в ответе `list_events`;
  опционально панель в Control UI.
- Поиск с подсветкой совпадений и фильтрами (тип, период).
- Предупреждение о конфликте встреч с предложением перенести.
- TTS-переключатель `/tts` и кнопка «повторить».
- Undo после создания/удаления.
- Мобильность — родные клиенты Telegram/WhatsApp; доступность — текстовая
  альтернатива голосу.
- Демо-режим с импортированным CSV и готовыми примерами запросов.

---

## 12. «Нормальная реализация», а не MVP

### Ядро (обязательно для сдачи)

- чистая архитектура: tools — тонкие адаптеры, бизнес-логика в services, без
  SQL и промптов в handlers;
- миграции (Drizzle/SQL), индексы, CHECK/EXCLUDE-ограничения, транзакции;
- demo-user + `openclaw_peer_id`, изоляция данных по `user_id` (полный auth — позже);
- таймауты, ретраи и fallback моделей — средствами OpenClaw;
- TypeBox-валидация всех tool-аргументов;
- structured logging через `api.logger` + `sessionKey`;
- тесты: unit (даты, слоты), integration (БД через testcontainers),
  e2e (создание → список → поиск через `openclaw agent`), golden-set NLU;
- CI: `tsc`, `oxlint`, Vitest, сборка плагина;
- Docker Compose: OpenClaw Gateway + PostgreSQL + установка плагина;
- healthchecks;
- README с архитектурой, решениями, trade-offs и планом улучшений;
- seed-скрипт и demo-данные.

### Production-hardening (после ядра)

- pairing/auth OpenClaw, gateway не в публичном интернете (Tailscale/SSH);
- rate limit на уровне каналов и плагина;
- напоминания — только через OpenClaw automations, без своего scheduler/Redis;
- Sentry/OTel, метрики, backup-стратегия;
- версионирование `SKILL.md` и автоматическая оценка регрессий;
- политика хранения аудио — средствами OpenClaw (удалять после распознавания
  или хранить N дней);
- graceful shutdown и нагрузочное тестирование.

Не делать:

- SQL-строки из LLM;
- хранение задач только в памяти/сессии LLM;
- «магические» регулярки на все случаи без тестов;
- один гигантский промпт на всё;
- доверие к датам от LLM без проверки;
- старт со своим scheduler/Redis/полным auth/мониторингом до стабильных
  4 сценариев;
- дублирование `sessions`/`messages` OpenClaw в доменной БД;
- публичный Gateway без pairing;
- секреты в репозитории.

---

## 13. Библиотеки: сводка

| Область | Библиотека | Зачем |
|---|---|---|
| Основа | `openclaw` | gateway, каналы, сессии, голос, automations |
| Плагин | `openclaw/plugin-sdk/*` | tools, lifecycle, config |
| Схемы | `@sinclair/typebox` | tool-схемы и валидация |
| БД | `pg`, `drizzle-orm`, `drizzle-kit` | доступ и миграции |
| Векторы | `pgvector` (SQL) | тип и операции |
| Даты | `chrono-node` | русские относительные даты |
| Время/таймзоны | `luxon` | границы дня/недели, UTC |
| Морфология | — | стемминг FTS `russian` + pg_trgm для опечаток |
| Нечёткий текст | `fastest-levenshtein` (опц.) | дедупликация |
| Эмбеддинги | Ollama/OpenAI-compatible API | bge-m3 (1024d) |
| Планировщик | OpenClaw automations | напоминания |
| Логи | `api.logger` | JSON-логи |
| Тесты | `vitest`, `testcontainers`, `nock`/`msw` | unit/integration |
| Качество | `typescript`, `oxlint`, `prettier`, `pre-commit` | стиль и типы |
| E2E | `openclaw agent` + `playwright` (опц.) | сквозные сценарии |

---

## 14. Этапы работ

| Этап | Результат |
|---|---|
| 0. Каркас | OpenClaw Gateway + PostgreSQL, плагин, manifest, миграции |
| 1. Домен | CRUD событий, список за период, demo-user/identity mapping, seed CSV |
| 2. NLU | skill, tools, `time_expression`, chrono-node, `pending_actions`, `ask_user` |
| 3. Поиск | текст → FTS → trigram → (флаг) vector/RRF/rerank, golden-set |
| 4. Голос | Telegram voice notes, STT/TTS OpenClaw, обязательный текстовый fallback |
| 5. Бонусы | update/delete/complete, конфликты, recurring, automations |
| 6. Полировка | тесты, CI, деплой, README, demo-ссылка; инфраструктура по необходимости |

---

## 15. Риски и mitigation

| Риск | Что делать |
|---|---|
| Плохое качество русского STT | OpenClaw STT (Groq/OpenAI/Deepgram), локальный whisper, `echoTranscript` |
| Лимиты бесплатных LLM | fallback-цепочка OpenClaw, retries, кэш ответов, локальная модель |
| LLM придумывает даты | `time_expression` + серверный DatetimeParser; ISO-даты от модели не принимаются |
| Неоднозначные фразы | `pending_action` + `ask_user`/явный вопрос |
| Несколько активных уточнений | partial unique index + деактивация предыдущего |
| Тяжёлые локальные эмбеддинги | флаг vector, API-эмбеддинги 1024d |
| Долгий ответ | стриминг текста OpenClaw, TTS после первого предложения |
| Конфликты встреч | EXCLUDE-ограничение + понятное сообщение |
| Деплой аудио | лимиты media OpenClaw, временные файлы, retention |
| Приватность | не логировать содержимое аудио, retention policy, ключи в secrets |
| Несовместимость версий OpenClaw | pin версии, plugin manifest, compat-тесты |
| Публичный Gateway | pairing, Tailscale/SSH, bind на localhost |

---

## 16. Что написать в README

1. Что это и какие сценарии работают.
2. Быстрый запуск: установка OpenClaw и `openclaw onboard`, `.env`, `docker compose up`
   (gateway + PostgreSQL), миграции, установка плагина, seed.
3. Архитектура и схема потоков (канал/голос → OpenClaw STT → агент + skill →
   tools → PostgreSQL → ответ/TTS).
4. Выбранные технологии и почему — не список, а «решение → причина»:
   OpenClaw (каналы, сессии, голос, automations), PostgreSQL (транзакции, FTS,
   trigram, EXCLUDE), pgvector (без отдельной vector DB), TypeBox (схемы
   инструментов), chrono-node (даты), `pending_actions` (уточнения).
5. Как устроен контекст и уточнения.
6. Как работает поиск (FTS + trigram, опционально vector/RRF/rerank) и какие
   флаги что включают.
7. Ограничения и что улучшил бы:
   - интеграция с Google Calendar/CalDAV;
   - повторяющиеся события и сложные правила напоминаний;
   - мультиустройство и identity linking (частично есть в OpenClaw);
   - улучшение ASR на именах/доменах;
   - A/B `SKILL.md` и автоматическая оценка качества.
8. Ссылка на демо и тестовые аккаунты.

---

## 17. Что подчеркнуть на демо и в README

1. OpenClaw — основа: каналы, сессии, память, голос и automations; свой
   агентский runtime не пишем.
2. LLM — оркестратор, а не хранилище данных.
3. Все действия выполняются через типизированные инструменты с TypeBox-валидацией.
4. Даты считает сервер, а не модель.
5. Все 4 обязательных сценария стабильны.
6. Свободные формулировки и синонимы, а не жёсткие команды.
7. Уточняющие вопросы при недостающих данных.
8. Данные сохраняются между запросами.
9. Поиск работает не только по точному совпадению.
10. Конфликты встреч контролируются на уровне БД.
11. Архитектура разделяет каналы, бизнес-логику, LLM, поиск и хранение.

---

## 18. Полезные ссылки

- OpenClaw — https://openclaw.ai/
- OpenClaw Docs — https://docs.openclaw.ai/
- OpenClaw GitHub — https://github.com/openclaw/openclaw
- Plugin SDK — https://docs.openclaw.ai/plugins/sdk-overview
- Skills — https://docs.openclaw.ai/tools/skills
- ClawHub — https://clawhub.ai/
- Telegram Bot API — https://core.telegram.org/bots/api
- PostgreSQL FTS — https://www.postgresql.org/docs/current/textsearch.html
- pgvector — https://github.com/pgvector/pgvector
- pg_trgm — https://www.postgresql.org/docs/current/pgtrgm.html
- chrono-node — https://github.com/wanasit/chrono
- TypeBox — https://github.com/sinclairzx81/typebox
- Drizzle ORM — https://orm.drizzle.team/
- BGE-M3 — https://huggingface.co/BAAI/bge-m3
- whisper.cpp — https://github.com/ggerganov/whisper.cpp
- edge-tts — https://github.com/rany2/edge-tts
- Docker — https://docs.docker.com/
