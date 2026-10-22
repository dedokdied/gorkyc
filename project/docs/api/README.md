# Контракт API (v1)

Источник правды для backend и frontend. Меняется только по договорённости обоих
участников: сначала правка здесь, потом код.

## Базовое

- Base URL: `/api/v1`
- Формат: JSON, UTF-8.
- Время: ISO 8601 с таймзоной (`2026-10-23T10:00:00+03:00`), хранение в UTC.
  Поля события (`starts_at`, `ends_at`, `due_at`) возвращаются в таймзоне
  события; `created_at`/`updated_at` — в UTC.
- Авторизация на время хакатона:
  - Telegram-бот: `X-Telegram-Id: <chat_id>` + `X-Bot-Secret: <secret>`;
  - Web: `X-Demo-User: demo`.
  Позже заменяется на JWT без изменения остальных DTO.
- Telegram-бот — тонкий клиент: сам не пишет в БД и не вызывает LLM.
- Ошибки:

```json
{
  "error": {
    "code": "validation_error",
    "message": "time_expression не распознан",
    "request_id": "..."
  }
}
```

`request_id` также возвращается в заголовке `X-Request-ID`. Если клиент передал
`X-Request-ID`, сервер сохраняет его; иначе генерирует новый. Коды ошибок:
`validation_error` (422), `not_found` (404), `meeting_overlap` (409),
`unauthorized` (401), `internal_error` (500).

## Владение эндпоинтами

| Метод | Путь | Владелец | Назначение |
|---|---|---|---|
| GET | `/events` | A | список за период |
| POST | `/events` | A | создать событие |
| GET | `/events/{id}` | A | получить событие |
| PATCH | `/events/{id}` | A | изменить |
| POST | `/events/{id}/complete` | A | отметить выполненным |
| DELETE | `/events/{id}` | A | удалить/отменить |
| POST | `/search` | A | поиск по старым записям |
| POST | `/chat` | B | текст → ответ ассистента |
| POST | `/voice` | B | аудио → расшифровка → ответ |
| GET | `/sessions/{id}/messages` | B | история диалога |
| POST | `/clarifications/{id}/answer` | B | ответ на уточнение |
| GET | `/healthz`, `/readyz` | вместе | health |

## DTO

### EventCreate

```json
{
  "type": "task",
  "title": "Позвонить Ивану",
  "description": null,
  "starts_at": null,
  "ends_at": null,
  "due_at": "2026-10-23T10:00:00+03:00",
  "duration_minutes": null,
  "timezone": "Europe/Moscow",
  "recurrence": null
}
```

Правила:

- `type`: `task`, `meeting`, `reminder`.
- Для `meeting` обязательны `starts_at` и `ends_at` (или `duration_minutes`,
  из которой backend считает `ends_at`).
- Для `reminder` обязателен `due_at`.
- `title` — 1–300 символов; пробелы по краям обрезаются.
- Даты должны быть timezone-aware. Naive datetime отклоняется (422).
- Если для встречи переданы и `ends_at`, и `duration_minutes`, они должны
  совпадать.
- `timezone` — IANA-таймзона (например, `Europe/Moscow`).
- `source` не принимается от клиента: источник проставляет сервер.

### EventRead

```json
{
  "id": "uuid",
  "type": "meeting",
  "status": "planned",
  "title": "Встреча с командой",
  "description": null,
  "starts_at": "2026-10-23T15:00:00+03:00",
  "ends_at": "2026-10-23T16:00:00+03:00",
  "due_at": null,
  "duration_minutes": 60,
  "timezone": "Europe/Moscow",
  "source": "text",
  "recurrence": null,
  "created_at": "2026-10-22T12:00:00Z",
  "updated_at": "2026-10-22T12:00:00Z",
  "completed_at": null
}
```

`source`: `text`, `voice`, `import`. `recurrence` — строка правила (например,
RRULE) или `null`; в текущем ядре не раскрывается в отдельные события.

`DELETE /events/{id}` удаляет событие. Статус `cancelled` зарезервирован для
будущего сценария отмены; текущий контракт не требует отдельного endpoint.

### EventPatch

Любое подмножество полей `EventCreate`, кроме `type` (тип не меняется).
`status` через PATCH не меняется: для завершения используется
`POST /events/{id}/complete`, для удаления — `DELETE`.

- Отсутствующее поле не меняется.
- Явный `null` очищает nullable-поле (`description`, `due_at`, `ends_at`,
  `recurrence`).
- Обязательные для типа поля нельзя очистить: `starts_at`/`ends_at` у встречи,
  `due_at` у напоминания.
- При переносе встречи пересчитывается `ends_at`; при изменении `ends_at`
  пересчитывается `duration_minutes`.

### Список событий

`GET /events?from=...&to=...&type=...`

- `from`/`to` — timezone-aware ISO 8601.
- В период попадают события, чей интервал пересекает `[from, to]`:
  `start = coalesce(starts_at, due_at)`,
  `end = coalesce(ends_at, due_at, starts_at)`.
- События без дат в выборку за период не попадают.
- `type` — `task`, `meeting`, `reminder`.

### SearchRequest

```json
{
  "query": "задача про договор",
  "type": null,
  "from": null,
  "to": null,
  "limit": 5
}
```

- `query` — 1–500 символов; пустая строка после `strip()` отклоняется.
- `type` — фильтр по типу события.
- `from`/`to` — timezone-aware ISO 8601, та же семантика периода, что у
  `GET /events`.
- `limit` — 1–50, по умолчанию 5.

### SearchHit

```json
{
  "event": { "id": "uuid", "type": "task", "title": "Проверить договор", "due_at": "..." },
  "score": 0.82,
  "snippet": "Проверить договор ..."
}
```

`score` — относительная релевантность: `0.7 * ts_rank_cd + 0.3 * similarity`
(PostgreSQL FTS + pg_trgm), не позиция в выдаче. `snippet` — начало
`search_text` (до 160 символов).

### Векторный поиск

В демо-окружении расширение `pgvector` недоступно, поэтому включён только
FTS + trigram. `embedding` хранится как JSONB-заглушка, флаг
`ENABLE_VECTOR_SEARCH=false`. Решение и условия включения —
`project/docs/decisions/0004-vector-search-deferred.md`.

### ChatRequest

```json
{
  "session_id": "uuid или null",
  "text": "Напомни завтра в 10 позвонить Ивану",
  "timezone": "Europe/Moscow"
}
```

`session_id = null` — backend создаёт сессию для текущего канала. Для Telegram
`external_id` сессии = `chat_id`, для web — id demo-сессии.

### VoiceRequest

`POST /voice` — `multipart/form-data`:

| Поле | Тип | Обязательно |
|---|---|---|
| `file` | аудио (OGG/MP3/WAV) | да |
| `session_id` | uuid | нет |
| `timezone` | string | нет |

Ответ:

```json
{
  "session_id": "uuid",
  "transcript": "напомни завтра в 10 позвонить ивану",
  "reply": "Создал напоминание: завтра в 10:00 — позвонить Ивану",
  "action": { "name": "create_event", "status": "done", "entity_id": "uuid" },
  "clarification": null,
  "audio_url": null
}
```

Если STT не распознал — `400` с `error.code = "stt_failed"`; бот просит
повторить или написать текстом.

### ChatResponse

```json
{
  "session_id": "uuid",
  "reply": "Создал напоминание: завтра в 10:00 — позвонить Ивану",
  "action": {
    "name": "create_event",
    "status": "done",
    "entity_id": "uuid"
  },
  "clarification": null,
  "audio_url": null
}
```

Уточнение:

```json
{
  "session_id": "uuid",
  "reply": "На какое время поставить встречу?",
  "action": null,
  "clarification": {
    "id": "pending-action-uuid",
    "question": "На какое время поставить встречу?",
    "options": ["10:00", "15:00", "Выбрать"],
    "missing": ["starts_at"]
  },
  "audio_url": null
}
```

## Примеры сценариев

### Создание задачи

```
POST /chat {"text": "Напомни завтра в 10 утра позвонить Ивану"}
→ 200 {"reply": "Создал напоминание: завтра в 10:00 — позвонить Ивану",
        "action": {"name": "create_event", "status": "done", "entity_id": "..."}}
```

### Уточнение

```
POST /chat {"text": "Поставь встречу с Иваном завтра"}
→ 200 {"clarification": {"id": "...", "question": "На какое время поставить встречу?", ...}}
POST /clarifications/{id}/answer {"text": "В 15:00"}
→ 200 {"reply": "Создал встречу с Иваном завтра в 15:00", "action": {...}}
```

### Список

```
POST /chat {"text": "Что у меня завтра?"}
→ 200 {"reply": "Завтра 2 события: ..."}
```

### Поиск

```
POST /search {"query": "задача про презентацию", "limit": 5}
→ 200 {"items": [{"event": {...}, "score": 0.9, "snippet": "..."}]}
```

## Важное различие

- **Публичный API** принимает готовые ISO-даты (`EventCreate`).
- **LLM-инструменты** принимают `time_expression` (исходную фразу), а сервер
  резолвит её в ISO. Модель не считает даты.
- `user_id` всегда берётся из `X-Telegram-Id`/`X-Demo-User`/auth, не из тела
  запроса.
- Telegram-бот не вызывает LLM напрямую: только backend.

## Клиенты

| Клиент | Заголовки | Что использует |
|---|---|---|
| Telegram-бот | `X-Telegram-Id`, `X-Bot-Secret` | `/chat`, `/voice`, `/events`, `/search` |
| Web (этап 2) | `X-Demo-User: demo` | те же эндпоинты |

## Изменения контракта

1. Обсудить в чате и записать сюда.
2. Обновить Pydantic-схемы и моки.
3. Обновить frontend-типы.
4. Только потом merge.
