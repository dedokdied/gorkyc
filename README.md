# Горький — голосовой ассистент задач и встреч

Прототип для хакатонного ТЗ: задачи, встречи и напоминания голосом и текстом.
Один backend обслуживает Telegram-бота и веб-клиент.

- **Работающий прототип:** <https://lustily-endowed-newfoundland.cloudpub.ru>
- **Основная документация:** [`project/README.md`](project/README.md)
- **Архитектура и запуск:** [`project/README.md`](project/README.md#быстрый-старт)
- **API:** [`project/docs/api/README.md`](project/docs/api/README.md)
- **Web-клиент:** [`project/docs/web.md`](project/docs/web.md)
- **Тесты LLM по ТЗ:** [`project/docs/llm-tests.md`](project/docs/llm-tests.md)
- **Журнал разработки:** [`project/DEVLOG.md`](project/DEVLOG.md)

## Что реализовано

- Создание задачи, встречи и напоминания из свободной формулировки.
- Относительные даты: «сегодня», «завтра», «послезавтра», «в пятницу»,
  «через два часа», «на следующей неделе», «до конца недели».
- Список событий за сегодня, завтра, неделю, 30 дней, произвольный диапазон,
  с фильтром по типу.
- Поиск старых записей: PostgreSQL FTS `russian` + `pg_trgm`, падежи и
  опечатки.
- Уточняющие вопросы, если не хватает даты, времени или содержания.
- Хранение в PostgreSQL: тип, название, дата/время, статус, автор, повтор.
- Голос: Web Speech API в браузере; серверный STT для Telegram.
- Веб-календарь и отдельная вкладка выполненных задач.
- Несколько пользователей, история диалога, защита от конфликтов встреч.

## Стек

FastAPI + SQLAlchemy 2 async + PostgreSQL, aiogram 3, React 18 + TypeScript +
Vite. LLM — OpenAI-compatible API с tool calling и rule-based fallback.

## Архитектура

```
Telegram-бот ─┐
              ├─> FastAPI /api/v1 ─> сервисы ─> репозитории ─> PostgreSQL
Web (React) ──┘                         │
                                       ├─ LLM (tool calling) + fallback
                                       ├─ DatetimeParser (даты/время)
                                       └─ поиск: FTS russian + pg_trgm
```

Бот и веб не дублируют бизнес-логику: оба ходят в один API. LLM выбирает
действие и передаёт исходное выражение времени, а сервер сам разбирает дату,
проверяет конфликты и сохраняет запись. Голос в вебе распознаётся и озвучивается
браузером; для Telegram есть серверный STT.

## Запуск

Полная инструкция — в [`project/README.md`](project/README.md). Кратко:

```bash
cd project
cp .env.example .env
docker compose -f infra/docker/docker-compose.yml up -d --build
```

Web: `http://localhost:8080`, API: `http://localhost:8000/api/v1/healthz`.

Секреты хранятся только в `project/.env` и `project/SECRETS.local.md`; оба файла
исключены из git. Не добавляйте PDF ТЗ, CSV-корпус и временные логи в репозиторий.
