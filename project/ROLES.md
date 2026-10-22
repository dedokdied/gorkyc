# Роли и рабочий контракт

Два участника, две вертикальные зоны. Сначала Telegram MVP, потом веб на том же
backend. Правило №1: не редактируем чужую зону без сообщения. Любое изменение
API или формата ответа — сначала в `docs/api/README.md`, потом в коде.

## Кто есть кто

| | Участник A | Участник B |
|---|---|---|
| **Роль** | Backend Core / Data & API | Assistant / Telegram & Web UX |
| **Главный результат** | БД, события, даты, поиск, API | LLM, tools, бот, голос, frontend, деплой |
| **Первый этап** | backend core + `/events`, `/search` | Telegram-бот + `/chat`, `/voice` |
| **Второй этап** | API для веба, стабильность, тесты | React-фронтенд, голос в браузере |
| **Не делает** | LLM-промпты, бота, фронтенд | Схему БД, SQL, доменные сервисы |

## Кто что делает

| Зона | A | B |
|---|---|---|
| PostgreSQL, миграции, модели | владелец | не меняет |
| `EventService`, CRUD, список | владелец | вызывает API |
| `DatetimeParser` | владелец | не меняет |
| Поиск FTS/trigram/pgvector | владелец | не меняет |
| Импорт CSV, seed | владелец | использует данные |
| `/events`, `/search`, health | владелец | не меняет |
| `/chat`, `/voice`, история | участвует в контракте | владелец |
| LLM, tool calling, `pending_actions` | не пишет промпты | владелец |
| STT/TTS | — | владелец |
| Telegram-бот | — | владелец |
| Scheduler напоминаний | владелец | notifier и UX |
| React frontend | — | владелец |
| Docker Compose, деплой | backend env и миграции | владелец |
| E2E, демо-сценарий | домен/поиск | владелец |
| README, `docs/demo.md` | разделы backend | владелец |

## Владение файлами

| Папка / файл | Владелец |
|---|---|
| `backend/app/models/`, `repositories/` | A |
| `backend/app/services/events.py`, `datetime_parser.py`, `search.py`, `reminders.py` | A |
| `backend/app/services/dialogue.py`, `assistant.py` | B |
| `backend/app/api/events.py`, `search.py`, `health.py` | A |
| `backend/app/api/chat.py`, `voice.py` | B |
| `backend/app/schemas/events.py`, `search.py` | A |
| `backend/app/schemas/chat.py`, `tools.py` | B |
| `backend/app/integrations/llm.py`, `stt.py`, `tts.py`, `telegram_notifier.py` | B |
| `backend/app/integrations/embeddings.py` | A |
| `backend/app/main.py`, `core/`, `workers/` | A |
| `backend/pyproject.toml`, `alembic.ini`, `migrations/` | A |
| `backend/tests/test_events.py`, `test_datetime_parser.py`, `test_search.py` | A |
| `backend/tests/test_chat.py` | B |
| `backend/tests/test_e2e.py` | вместе |
| `telegram_bot/` | B |
| `frontend/` | B |
| `.env.example` | B (A даёт `DATABASE_URL` и backend-переменные) |
| `infra/docker/docker-compose.yml` | B (A даёт backend env и миграции) |
| `infra/docker/Dockerfile.backend` | A |
| `infra/docker/Dockerfile.bot`, `Dockerfile.frontend` | B |
| `infra/deploy/` | B |
| `scripts/import_csv.py`, `seed_demo.py`, `eval_search.py` | A |
| `scripts/e2e/` | B |
| `docs/api/README.md` | A — events/search; B — chat/voice; merge через PR |
| `docs/demo.md` | B |
| `README.md` | B |
| `docs/decisions/`, `PLAN.md` | вместе |

## Стыки без пересечений

| Что | Кто делает | Кто не лезет |
|---|---|---|
| `/events`, `/search`, БД, даты | A | B не пишет SQL и не меняет модели |
| `/chat`, `/voice`, LLM, tools | B | A не пишет промпты и не меняет ответы ассистента |
| `backend/app/main.py` | A регистрирует роутеры | B просит A подключить новый роутер |
| `TelegramNotifier` | A вызывает при due, B реализует отправку | A не импортирует aiogram |
| `docker-compose.yml` | B | A даёт `Dockerfile.backend`, env и команду миграций |
| `.env.example` | B | A даёт только backend-переменные |
| `docs/api/README.md` | A — events/search, B — chat/voice | без PR контракт не меняем |
| `PLAN.md`, ADR | вместе | изменения только через PR |

## Контракт API — фиксируем в первый час

Базовый префикс: `/api/v1`.

```text
GET/POST   /events
GET/PATCH  /events/{id}
DELETE     /events/{id}
POST       /events/{id}/complete
POST       /search
POST       /chat
POST       /voice
GET        /sessions/{id}/messages
POST       /clarifications/{id}/answer
GET        /healthz, /readyz
```

Формат `/chat`:

```json
{
  "session_id": "uuid",
  "reply": "Создал встречу: завтра, 15:00 — Иван",
  "action": { "name": "create_event", "status": "done", "entity_id": "uuid" },
  "clarification": null,
  "audio_url": null
}
```

Уточнение:

```json
{
  "session_id": "uuid",
  "reply": "Во сколько поставить встречу?",
  "action": null,
  "clarification": {
    "id": "uuid",
    "question": "Во сколько?",
    "options": ["10:00", "15:00", "Выбрать"],
    "missing": ["starts_at"]
  }
}
```

Правила:

- `user_id` берётся из `X-Telegram-Id`/`X-Demo-User`, не из тела запроса.
- Telegram-бот передаёт `X-Bot-Secret`; снаружи API не доступен.
- LLM передаёт `time_expression`, а не ISO-даты.
- Ошибки — кодами, без SQL и stack trace.

## Интерфейс напоминаний

A отвечает за выборку due-напоминаний, B — за отправку в Telegram.

```python
class ReminderNotifier(Protocol):
    async def send(self, telegram_id: int, text: str) -> None: ...
```

## Первый час — вместе

- Зафиксировать `docs/api/README.md`: DTO, ошибки, chat/voice.
- Определить demo-user и маппинг Telegram `chat_id → user_id`.
- A: схемы БД, миграции, stub `/events`, `/search`.
- B: skeleton `telegram_bot`, `/chat` на моках, `.env.example`.
- Поднять Docker Compose: `api`, `postgres`, `bot`.

## Правила, чтобы не мешать

1. A работает в `feat/core-*`, B — в `feat/assistant-*`.
2. Один активный PR на человека; общие файлы — отдельным маленьким PR.
3. Сначала заглушка/интерфейс, потом реализация — второй не ждёт.
4. Моки обязательны: A тестирует домен без LLM, B тестирует бота на mock API.
5. Контракт меняем только через `docs/api/README.md` и сообщение в чат.
6. Секреты — только в env/secrets, никогда в git.
7. Синк на старте и в конце дня: 15 минут, только блокеры и контракт.

## Definition of Done

### Telegram MVP

- A: миграции, CRUD, даты, поиск, seed, тесты домена.
- B: бот работает, текст и голос, уточнения, `/chat`, `/voice`, деплой.
- Вместе: 4 сценария, напоминание, данные после перезапуска, README.

### Web

- A: API стабилен, CORS, тесты, demo-user.
- B: React-чат, таймлайн, поиск, карточки, голос, адаптив.
- Вместе: те же 4 сценария в браузере и демо-ссылка.
