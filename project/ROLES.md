# Роли и параллельная работа

Два участника, две вертикальные зоны ответственности. Задача — не пересекаться по
файлам и не блокировать друг друга. Контракт API и интерфейсы фиксируются в первый
час, дальше каждый работает в своей папке.

| | Участник A | Участник B |
|---|---|---|
| **Роль** | Core / Data & Retrieval | Assistant / UX & Integrations |
| **Главный результат** | Надёжные данные, CRUD, список, даты, поиск | Диалог, LLM, голос, интерфейс, деплой |
| **Основные папки** | `backend/app/{models,repositories,services,api}/...`, `backend/migrations`, `backend/tests` | `backend/app/{api,services}/chat*`, `backend/app/integrations`, `frontend`, `infra/deploy` |

## Участник A — Core / Data & Retrieval

### Обязанности

- Схема БД и миграции Alembic: `users`, `events`, `sessions`, `messages`,
  `pending_actions`.
- SQLAlchemy-модели, репозитории, транзакции.
- `EventService`: создание, изменение, удаление, отметка выполнения,
  список за период, фильтры.
- `DatetimeParser`: `time_expression` → `starts_at`/`due_at`, `duration_expression`
  → `ends_at`; относительные даты, таймзона, уточнения при неоднозначности.
- Лексический поиск: FTS `russian`, `pg_trgm`, ранжирование.
- Импорт CSV и seed-данные.
- Эндпоинты `/api/v1/events` и `/api/v1/search`.
- Unit- и integration-тесты домена и поиска.
- Ведение `docs/api/README.md` совместно с B (A — владелец схем).

### Не делает

- Не пишет UI и не подключает голос.
- Не пишет промпты и tool calling.
- Не деплоит фронтенд.

## Участник B — Assistant / UX & Integrations

### Обязанности

- LLM-адаптер через LiteLLM/OpenAI-compatible, провайдеры и fallback.
- Tool calling: `create_event`, `update_event`, `complete_event`, `delete_event`,
  `list_events`, `search_events`, `ask_clarification`.
- `DialogueService`: контекст, `pending_actions`, уточнения, `last_entity_id`,
  «перенеси её на завтра».
- Эндпоинты `/api/v1/chat`, `/api/v1/voice`, история сессии.
- STT: запись аудио, faster-whisper/VAD/API; TTS: edge-tts/Silero.
- Frontend: чат, история, карточки событий, таймлайн, поиск, настройки.
- Деплой прототипа и демо-ссылка.
- Тесты ассистента и e2e-сценарии.

### Не делает

- Не меняет схему БД без A.
- Не пишет SQL и миграции.
- Не переписывает `EventService` — только вызывает его интерфейс.

## Общие зоны (делаем вместе)

- `docs/api/README.md` — контракт и примеры.
- `pyproject.toml`, `.env.example`, `docker-compose.yml`, `main.py`.
- CI, интеграционные тесты, README, демо-сценарий.
- Финальная проверка 4 обязательных сценариев.

## Владение файлами

| Папка / файл | Владелец | Комментарий |
|---|---|---|
| `backend/app/models/` | A | модели и связи |
| `backend/app/repositories/` | A | SQL-запросы |
| `backend/app/schemas/` | A (основа), B (chat-схемы) | изменения — по договорённости |
| `backend/app/services/events.py` | A | доменная логика событий |
| `backend/app/services/datetime_parser.py` | A | разбор дат |
| `backend/app/services/search.py` | A | FTS + trigram; vector — опционально |
| `backend/app/services/dialogue.py` | B | контекст и уточнения |
| `backend/app/api/events.py` | A | CRUD и список |
| `backend/app/api/search.py` | A | поиск |
| `backend/app/api/chat.py` | B | чат и голос |
| `backend/app/integrations/llm*` | B | провайдеры LLM |
| `backend/app/integrations/stt*`, `tts*` | B | голос |
| `backend/app/integrations/embeddings*` | A | эмбеддинги (если включены) |
| `backend/migrations/` | A | Alembic |
| `backend/tests/` | A: домен, B: ассистент, e2e — вместе | тесты по зонам |
| `frontend/` | B | весь UI |
| `infra/docker/` | вместе | A — backend/db, B — frontend |
| `infra/deploy/` | B | деплой |
| `scripts/import_csv.py` | A | импорт |
| `scripts/eval_search.py` | A | качество поиска |
| `docs/api/` | вместе | контракт |
| `docs/decisions/` | вместе | ADR |

## Интерфейсы, которые фиксируем в первый час

```python
class EventService(Protocol):
    async def create(self, user_id, data: EventCreate) -> EventRead: ...
    async def update(self, user_id, event_id, data: EventPatch) -> EventRead: ...
    async def complete(self, user_id, event_id) -> EventRead: ...
    async def delete(self, user_id, event_id) -> None: ...
    async def list(self, user_id, period: Period, type: EventType | None) -> list[EventRead]: ...
    async def get(self, user_id, event_id) -> EventRead: ...

class SearchService(Protocol):
    async def search(self, user_id, query: str, filters: SearchFilters) -> list[SearchHit]: ...

class DatetimeParser(Protocol):
    def parse(self, expression: str, tz: str, now: datetime) -> ParsedTime: ...
```

Формат `ParsedTime`: `starts_at`, `ends_at`, `due_at`, `precision`,
`ambiguous`, `clarification`.

## План по дням (пример на 2 дня)

### День 1, утро — вместе, 1–2 часа

- Зафиксировать `docs/api/README.md`: эндпоинты, DTO, ошибки.
- Создать Pydantic-схемы и заглушки сервисов.
- Поднять Docker Compose: `api`, `postgres`, `frontend` (без Redis).
- Договориться о demo-user и заголовке авторизации.
- Создать ветки `feat/core-*` и `feat/assistant-*`.

### День 1, день — параллельно

**A:**
- миграции и модели;
- CRUD событий;
- список за период;
- seed из CSV;
- тесты репозиториев и CRUD.

**B:**
- каркас React-страницы;
- mock API (`VITE_USE_MOCKS=true`);
- LLM-адаптер и tool-схемы на моках;
- запись аудио и STT proof-of-concept;
- карточки и история диалога.

### День 1, вечер — интеграция

- B подключает реальные `/events` к чату.
- A добавляет `DatetimeParser` и уточнения.
- Вместе проверяют: «Напомни завтра в 10…», «Встреча в пятницу в 15:00».
- Фиксируют найденные расхождения контракта.

### День 2, утро — параллельно

**A:**
- FTS + trigram + ранжирование;
- импорт CSV и golden-set;
- тесты поиска и дат.

**B:**
- `pending_actions` и контекст;
- TTS и полный голосовой цикл;
- полировка UI;
- деплой.

### День 2, день — вместе

- Проверка 4 обязательных сценариев.
- Исправление интеграционных багов.
- README, демо-сценарий, скриншоты.
- Финальный прогон тестов и деплой.

## Оценка нагрузки (16 часов на участника)

| A | Часы | B | Часы |
|---|---:|---|---:|
| Схема БД, миграции | 2 | Каркас и UI чата | 3 |
| CRUD + список | 3 | LLM tool calling | 3 |
| DatetimeParser | 2 | `pending_actions`, контекст | 3 |
| Импорт CSV + seed | 1 | STT/TTS | 2 |
| FTS + trigram | 3 | Деплой и демо | 2 |
| Тесты домена/поиска | 2 | Тесты ассистента/e2e | 2 |
| Контракт, CI, общие файлы | 3 | Контракт, README, общие файлы | 1 |
| **Итого** | **16** | **Итого** | **16** |

Семантический поиск и rerank — бонус, делается только после стабильного ядра.
Если остаётся время, A добавляет pgvector, B — полировку UX.

## Правила, чтобы не мешать друг другу

1. Не редактировать чужую папку без сообщения в чат.
2. Любое изменение API-контракта — сначала в `docs/api/README.md`, потом в коде.
3. Общие файлы менять маленькими PR, не «заодно».
4. Моки и feature flags обязательны: каждый должен запускать свою часть без
   готовности второй.
5. Перед merge — `ruff`, `mypy`, `pytest`; для фронта — `npm run build`.
6. Если задача блокирует другого — сначала интерфейс/заглушка, потом реализация.
7. Один человек — один активный PR, чтобы не плодить конфликты.

## Definition of Done

- 4 обязательных сценария работают end-to-end.
- Данные сохраняются между запросами.
- Уточняющий диалог работает: «Поставь встречу с Иваном завтра» → «Во сколько?».
- Поиск находит записи по смыслу/падежам, а не только по точному тексту.
- Голосовой цикл работает, текстовый ввод — всегда доступен.
- README позволяет поднять проект с нуля.
- Демо-ссылка открывается и не падает на базовых сценариях.
