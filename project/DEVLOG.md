# DEVLOG — журнал проекта

> **Правило:** перед каждым коммитом добавь сюда запись по шаблону в конце:
> что добавили, что проверили, что осталось. Это точка входа для следующего
> разработчика или AI-агента: не нужно заново читать весь код, чтобы понять
> текущее состояние.

## Как быстро войти в курс

- **Проект:** голосовой ассистент задач и встреч для хакатона «Горький код».
- **Роль B:** Telegram-бот, диалог, LLM-инструменты, уточнения, голос.
- **Стек:** FastAPI + SQLAlchemy 2 async + PostgreSQL, aiogram 3, React + Vite.
- **Один backend:** бот и веб — тонкие клиенты к `/api/v1`, бизнес-логика не
  дублируется.
- **Главные файлы:**
  - `backend/app/services/assistant.py` — цикл LLM + tool calling, уточнения,
    история диалога.
  - `backend/app/services/assistant_tools.py` — выполнение инструментов и
    разбор дат.
  - `backend/app/api/deps.py` — авторизация и `user_id`.
  - `telegram_bot/app/handlers/` — `/start`, онбординг, текст, голос, события.
  - `telegram_bot/app/identity.py` — Telegram-аккаунт vs chat id.
  - `frontend/src/` — веб-клиент.
- **Команды:**
  ```bash
  cd project/backend && .venv/Scripts/python -m pytest -q
  cd project/telegram_bot && .venv/Scripts/python -m pytest -q
  cd project/frontend && npm run build
  ```
- **Секреты:** только в `project/.env` и `project/SECRETS.local.md`, в git не
  попадают. Не печатать значения в логах и ответах.

## Текущее состояние (2026-10-26)

- Telegram MVP работает: текст, создание/список/поиск/уточнения, напоминания,
  `/link` и `/settings`.
- Веб-версия: регистрация/вход, чат, таймлайн, поиск, профиль с таймзоной,
  in-app напоминания, редактирование и повтор событий.
- История диалога и `pending_actions` хранятся в PostgreSQL и переживают
  рестарт backend и перезагрузку страницы.
- Web-auth: PBKDF2-хеш пароля, HMAC access-token, `Authorization: Bearer`.
  `X-Demo-User` оставлен только для legacy/тестов.
- Данные разделены по `user_id`: `events.user_id` + фильтры в репозиториях.
- Бот определяет пользователя по `message.from_user.id` (аккаунт Telegram), а
  не по `chat.id`; `@username` сохраняется только для отображения.
- LLM получает последние 12 сообщений диалога; полная история — в `messages`.
- Ответ текстом на уточнение попадает в pending-action, а не создаёт новый
  запрос.
- Голосовые функции отложены: `STT_PROVIDER=none`, `TTS_PROVIDER=none`.

## Журнал изменений

### 2026-10-26 — Напоминания на сайте, редактирование, повтор, таймзона

**Добавили:**
- `DbPendingActionStore`: уточнения теперь в PostgreSQL, очищаются вместе с
  чатом.
- In-app напоминания: `GET /reminders/inbox`, `POST /reminders/{id}/ack`,
  баннер и polling на фронтенде.
- Редактирование события в таймлайне (`PATCH /events/{id}`) и повтор
  `daily`/`weekly`/`monthly`; при `complete` создаётся следующий экземпляр.
- `PATCH /auth/me` (имя, таймзона, onboarding), выбор таймзоны в профиле и
  использование сохранённой таймзоны в чате; `/settings` в боте.
- Alias истории `GET|DELETE /sessions/{id}/messages` к `/chat/history`.
- `onboarding_seen` перенесён из MemoryStorage в `users`.
- Схема выровнена: `sessions.channel/external_id`, `messages.tool_name/
  tool_payload`, `pending_actions.question/options`, `events.web_ack_at`.

**Проверили:**
- Backend: `107 passed` (PostgreSQL, миграции через `Base.metadata.create_all`).
- Bot: `28 passed`.
- Frontend: `npm run build` и Playwright e2e `8 passed`.
- Миграция `0007_schema_align` применяется при старте контейнера.
- Живые endpoint'ы: `PATCH /auth/me`, `GET /reminders/inbox`,
  `POST /reminders/{id}/ack`, `GET|DELETE /sessions/{id}/messages`.
- Найдено и исправлено: `pending_actions.user_id` из БД — строка, а endpoint
  получал `UUID`; сравнение всегда было истинным, поэтому любое уточнение
  считалось чужим. Теперь идентификаторы сравниваются как строки.

**Осталось:**
- Голос (STT/TTS) — отложен.
- Публичная демо-ссылка/деплой.

### 2026-10-25 — Web-версия: аккаунты, монохромный UI, ASCII-робот

**Добавлено**

- `backend/app/core/security.py`: PBKDF2-SHA256 для паролей, HMAC-SHA256
  access-токены без внешних зависимостей.
- `backend/app/api/auth.py`, `backend/app/schemas/auth.py`: регистрация,
  вход, `/auth/me`, stateless logout.
- Миграция `0004_web_auth`: `users.password_hash`.
- `backend/app/api/deps.py`: `Authorization: Bearer` как основной web-auth;
  `get_authenticated_user` для `/auth/me`; `ALLOW_DEMO_AUTH` для legacy.
- `/chat` и `/voice` прокидывают Bearer-токен в резолвер пользователя.
- Frontend: экран входа/регистрации, `useAuth`, auth-клиент, ASCII-робот,
  полностью новый чёрно-белый интерфейс, адаптив.
- E2E переведён с demo-заголовка на реальный аккаунт и токен.
- Документация: `docs/web.md`, обновлены README, API-контракт и
  `.env.example`.

**Проверено**

- `python -m compileall app tests` — синтаксис.
- `ruff check app tests` — без замечаний.
- 51 backend-тест без PostgreSQL — проходят.
- `npm run build` — production-сборка проходит (Node 22, Vite 6).
- Backend auth-тесты добавлены; запуск требует PostgreSQL.

**Осталось**

- Прогнать полный backend pytest с PostgreSQL и Playwright e2e.
- Refresh-токены, httpOnly cookie, отзыв сессий.
- Персистентность истории диалога и pending-actions.
- Веб-напоминания (in-app/Web Push).
- Редактирование события в UI.

### 2026-10-24 — MVP: пользователи, онбординг, контекст диалога

**Добавлено**

- `backend/app/core/config.py`: `.env` ищется от корня `project/`, а не от
  текущей директории. Добавлены настройки `LLM_TIMEOUT`, `STT_*`.
- `backend/app/integrations/llm.py`, `stt.py`: билдеры читают `Settings`, а не
  `os.getenv`; локально теперь реально включается API-провайдер из `.env`.
- `backend/app/api/deps.py`: заголовок `X-Telegram-Username`, нормализация
  `@username`, `display_name` в БД. Идентичность — по числовому Telegram id.
- `telegram_bot/app/identity.py`: единый helper `from_user.id` / `@username`.
- Все handler'ы бота переведены с `chat.id` на `from_user.id` (важно для
  групп).
- `backend/app/services/dialogue.py`: `InMemoryConversationStore` — последние
  4 сообщения на пользователя.
- `backend/app/services/assistant.py`:
  - история передаётся в LLM перед текущим сообщением;
  - ответ на `ask_clarification` уходит обратно в LLM с историей;
  - ответ на уточнение раскладывается в нужное поле (`title`, время,
    длительность, описание);
  - если LLM вызывает `create_event` без названия, пользователь получает
    вопрос «Что нужно сделать?», а не техническую ошибку;
  - ошибки инструментов больше не превращаются в «Готово.»;
  - в системный промпт добавлен запрет предлагать кнопки.
- `backend/app/schemas/chat.py`, `api/chat.py`: `timezone` в ответе на
  уточнение.
- `telegram_bot/app/handlers/onboarding.py`, `app/onboarding.py`,
  `app/keyboards.py`: онбординг и меню.
- `telegram_bot/app/handlers/text.py`: текст при активном уточнении идёт в
  `/clarifications/{id}/answer`; добавлен `/cancel`.
- Тесты: история диалога, `ask_clarification`, изоляция по Telegram-аккаунту,
  username, онбординг-клавиатуры, создание события без названия.

**Проверено**

- `backend: ruff check app tests` — чисто.
- `backend: pytest` без БД — 30 passed.
- `bot: pytest` — 20 passed.
- Запуск из `project/backend` видит `.env`: БД `127.0.0.1:5434/assistant`,
  LLM `api` + ключ, клиент `FallbackLLM`.

**Осталось**

- Прогнать полный backend-набор с PostgreSQL (24 теста) и e2e.
- История и pending-actions пока in-memory: после рестарта теряются. Таблицы
  `sessions`, `messages`, `pending_actions` уже есть — перенести туда.
- `GET /sessions/{id}/messages` всё ещё описан в контракте, но не реализован.
- Напоминания уходят только Telegram-пользователям, веб-демо их не получает.
- Нет `/settings` для таймзоны; `answer_clarification` теперь принимает
  timezone, но бот всегда берёт `APP_TZ`.
- Запрет на «нажми кнопку» — только в промпте. Если модель начнёт игнорировать,
  добавить детерминированную постобработку.
- `onboarding_seen` живёт в `MemoryStorage` и сбрасывается при рестарте бота.
- В `telegram_bot/app/api_client.py` `list_events` всё ещё отправляет
  `status`/`limit`, которые backend не принимает (игнорируются).

## Бэклог

### Ближайшее (MVP)

- [ ] PostgreSQL + полный `pytest` + smoke/e2e.
- [ ] Персистентность истории диалога и pending-actions.
- [ ] `GET /sessions/{id}/messages` по контракту.
- [ ] Таймзона пользователя: `/settings` или определение из Telegram.
- [ ] Проверить сценарий группы: бот отвечает в группе, но данные у каждого
      участника свои.
- [ ] Обновить README, если поведение бота изменилось.

### Потом: авторизация и разделение БД в веб-версии

Не делать в рамках текущего MVP. Когда дойдём:

- добавить `auth`-модуль: email+password или OAuth, JWT access/refresh;
- `user_id` брать из токена, а не из `X-Demo-User`;
- оставить `X-Telegram-Id` + `X-Bot-Secret` для бота;
- в `users` добавить `email`, `password_hash` или таблицу OAuth-identity;
- на фронте — страница входа, хранение токена, `Authorization: Bearer ...`;
- тесты: пользователь A не видит события пользователя B по токену.

Схема БД уже готова к этому: `events.user_id` и фильтры по нему есть.

## Шаблон записи

```markdown
### YYYY-MM-DD — короткое название

**Добавлено**
- ...

**Изменено**
- ...

**Проверено**
- ...

**Осталось**
- ...
```
