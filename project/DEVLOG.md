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
  - `frontend/src/` — веб-демо.
- **Команды:**
  ```bash
  cd project/backend && .venv/Scripts/python -m pytest -q
  cd project/telegram_bot && .venv/Scripts/python -m pytest -q
  cd project/frontend && npm run build
  ```
- **Секреты:** только в `project/.env` и `project/SECRETS.local.md`, в git не
  попадают. Не печатать значения в логах и ответах.

## Текущее состояние (2026-10-24)

- Telegram MVP работает: текст, голос, создание/список/поиск/уточнения,
  напоминания.
- Веб-демо работает на том же API: чат, таймлайн, поиск, голосовой ввод.
- Данные разделены по `user_id`: `events.user_id` + фильтры в репозиториях.
- Бот определяет пользователя по `message.from_user.id` (аккаунт Telegram), а
  не по `chat.id`; `@username` сохраняется только для отображения.
- LLM получает последние 4 сообщения диалога и видит свои уточняющие вопросы.
- Ответ текстом на уточнение попадает в pending-action, а не создаёт новый
  запрос.
- Первый экран `/start`: «Начать» / «Примеры», затем «Сделать задачу» /
  «Мои планы».
- Backend: 30 тестов без БД проходят; 24 теста требуют PostgreSQL. Bot: 20
  тестов проходят. Frontend: сборка проверялась ранее, изменений нет.

## Журнал изменений

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
