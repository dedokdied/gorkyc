# Контракт API (v1)

Источник правды для backend и frontend. Меняется только по договорённости обоих
участников: сначала правка здесь, потом код.

## Базовое

- Base URL: `/api/v1`
- Формат: JSON, UTF-8.
- Время: ISO 8601 с таймзоной (`2026-10-23T10:00:00+03:00`), хранение в UTC.
  Поля события (`starts_at`, `ends_at`, `due_at`) возвращаются в таймзоне
  события; `created_at`/`updated_at` — в UTC.
- Авторизация:
  - Web: `Authorization: Bearer <access_token>`; токен выдаётся
    `/auth/register` и `/auth/login`;
  - Telegram-бот: `X-Telegram-Id: <user_id>` + `X-Bot-Secret: <secret>`;
  - `X-Telegram-Username: @username` — необязательный заголовок только для
    отображения; идентичность всегда определяется по числовому `user_id`;
  - `X-Demo-User: demo` — legacy/тестовый режим, включается
    `ALLOW_DEMO_AUTH=true`; в production выключается;
  - при наличии Telegram-заголовков они имеют приоритет над Bearer.
- Access-токен подписан HMAC-SHA256 и живёт `WEB_TOKEN_TTL_SECONDS`
  (по умолчанию 7 дней). Refresh-токены и отзыв сессий — следующий этап.
- CORS для web: origin(ы) из `WEB_ORIGIN` (список через запятую).
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
| POST | `/auth/register` | B | регистрация web-аккаунта |
| POST | `/auth/login` | B | вход, выдача access-токена |
| GET | `/auth/me` | B | профиль (Bearer или Telegram-заголовки) |
| PATCH | `/auth/me` | B | имя, таймзона, onboarding |
| POST | `/auth/link-telegram` | B | привязать Telegram по коду |
| POST | `/auth/logout` | B | no-op для stateless-токена |
| POST | `/telegram/link-code` | B | одноразовый код для привязки |
| GET | `/events` | A | список за период |
| POST | `/events` | A | создать событие |
| GET | `/events/{id}` | A | получить событие |
| PATCH | `/events/{id}` | A | изменить |
| POST | `/events/{id}/complete` | A | отметить выполненным |
| DELETE | `/events/{id}` | A | удалить/отменить |
| POST | `/search` | A | поиск по старым записям |
| POST | `/chat` | B | текст → ответ ассистента |
| POST | `/voice` | B | аудио → расшифровка → ответ |
| POST | `/clarifications/{id}/answer` | B | ответ на уточнение |
| GET | `/chat/history?session_id=...` | B | история диалога |
| DELETE | `/chat/history?session_id=...` | B | очистить диалог |
| GET | `/sessions/{id}/messages` | B | alias истории диалога |
| DELETE | `/sessions/{id}/messages` | B | alias очистки диалога |
| GET | `/reminders/inbox` | A | напоминания для in-app баннера |
| POST | `/reminders/{id}/ack` | A | закрыть напоминание на сайте |
| GET | `/healthz`, `/readyz` | вместе | health |

## Auth DTO

### RegisterRequest

```json
{
  "email": "you@example.com",
  "password": "минимум 8 символов",
  "display_name": "Иван",
  "timezone": "Europe/Moscow"
}
```

`display_name` и `timezone` необязательны. Email нормализуется в нижний
регистр. Пароль хешируется на сервере (PBKDF2-SHA256) и никогда не
возвращается.

### LoginRequest

```json
{
  "email": "you@example.com",
  "password": "пароль"
}
```

### AuthResponse

```json
{
  "access_token": "header.payload.signature",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "Иван",
    "timezone": "Europe/Moscow",
    "created_at": "2026-10-25T12:00:00Z",
    "telegram_linked": false,
    "telegram_username": null,
    "onboarding_seen": true
  }
}
```

`PATCH /auth/me` принимает любое подмножество `display_name`, `timezone`,
`onboarding_seen`. Таймзона проверяется через IANA `ZoneInfo`. `/auth/me`
работает и с Bearer, и с Telegram-заголовками, поэтому бот использует его для
`/settings`.

Ошибки: `409 email_taken` при повторной регистрации, `401
invalid_credentials` при неверной паре email/пароль.

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

`source`: `text`, `voice`, `import`. `recurrence`: `daily`, `weekly`,
`monthly` или `null`. При `POST /events/{id}/complete` повторяющееся событие
создаёт следующий экземпляр (`status=planned`, `parent_id` указывает на
первый экземпляр).

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
`external_id` сессии = `chat_id`, для web — id сессии, сохранённый в
localStorage. История и pending-actions пока in-memory.

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

## История диалога

`GET /chat/history?session_id=<uuid>` и alias
`GET /sessions/<uuid>/messages` возвращают список:

```json
[
  {"id": "uuid", "role": "user", "content": "Напомни завтра", "created_at": "..."},
  {"id": "uuid", "role": "assistant", "content": "Готово.", "created_at": "..."}
]
```

История хранится в PostgreSQL (`sessions` + `messages`) и привязана к паре
`user_id` + `session_id`. Чужую сессию нельзя прочитать или очистить.
`DELETE` с тем же путём удаляет сообщения и сессию, а также незавершённое
уточнение этой сессии.

## Напоминания на сайте

- `GET /reminders/inbox` — напоминания, у которых `due_at <= now`,
  `status=planned` и `web_ack_at IS NULL`.
- `POST /reminders/{id}/ack` — закрыть напоминание в веб-интерфейсе
  (`web_ack_at=now`). Telegram-доставка учитывается отдельно через
  `reminder_sent_at`, поэтому баннер и сообщение бота не мешают друг другу.

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
POST /clarifications/{id}/answer {"text": "В 15:00", "timezone": "Europe/Moscow"}
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
- `user_id` всегда берётся из `Authorization: Bearer` /
  `X-Telegram-Id` / legacy `X-Demo-User`, не из тела запроса. Все запросы к
  событиям и поиску фильтруются по этому `user_id`.
- Telegram-бот не вызывает LLM напрямую: только backend.
- Для групповых чатов бот использует `message.from_user.id`, а не `chat.id`,
  поэтому участники группы не смешиваются в одного пользователя.

## Клиенты

| Клиент | Заголовки | Что использует |
|---|---|---|
| Telegram-бот | `X-Telegram-Id`, `X-Telegram-Username`, `X-Bot-Secret` | `/chat`, `/voice`, `/events`, `/search`, `/auth/me`, `/telegram/link-code` |
| Web | `Authorization: Bearer <token>` | `/auth/*`, `/chat`, `/chat/history`, `/reminders/*`, `/voice`, `/events`, `/search` |
| Legacy / тесты | `X-Demo-User: demo` | те же эндпоинты при `ALLOW_DEMO_AUTH=true` |

## Изменения контракта

1. Обсудить в чате и записать сюда.
2. Обновить Pydantic-схемы и моки.
3. Обновить frontend-типы.
4. Только потом merge.
