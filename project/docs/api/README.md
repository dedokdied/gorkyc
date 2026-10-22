# Контракт API (v1)

Источник правды для backend и frontend. Меняется только по договорённости обоих
участников: сначала правка здесь, потом код.

## Базовое

- Base URL: `/api/v1`
- Формат: JSON, UTF-8.
- Время: ISO 8601 с таймзоной (`2026-10-23T10:00:00+03:00`), хранение в UTC.
- Авторизация на время хакатона: demo-user. Заголовок `X-Demo-User: demo`
  (позже заменяется на JWT без изменения остальных DTO).
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
- `title` — 1–300 символов.

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
  "created_at": "2026-10-22T12:00:00Z",
  "updated_at": "2026-10-22T12:00:00Z",
  "completed_at": null
}
```

### EventPatch

Любое подмножество полей `EventCreate`, кроме `type` (тип не меняется). При
переносе встречи пересчитывается `ends_at`.

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

### SearchHit

```json
{
  "event": { "id": "uuid", "type": "task", "title": "Проверить договор", "due_at": "..." },
  "score": 0.82,
  "snippet": "Проверить договор ..."
}
```

### ChatRequest

```json
{
  "session_id": "uuid или null",
  "text": "Напомни завтра в 10 позвонить Ивану",
  "timezone": "Europe/Moscow"
}
```

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
- `user_id` всегда берётся из `X-Demo-User`/auth, не из тела запроса.

## Изменения контракта

1. Обсудить в чате и записать сюда.
2. Обновить Pydantic-схемы и моки.
3. Обновить frontend-типы.
4. Только потом merge.
