# 0005 — Напоминания: asyncio worker вместо APScheduler

Дата: 2026-10-26

## Контекст

В `PLAN.md` для напоминаний указан APScheduler с PostgreSQL job store.
Фактическая реализация — `ReminderWorker` на `asyncio`: раз в
`REMINDERS_INTERVAL_SECONDS` он выбирает просроченные `reminder`-события
(`due_at <= now`, `reminder_sent_at IS NULL`), отправляет их в Telegram и
проставляет `reminder_sent_at`.

## Решение

Оставляем простой worker для хакатонного MVP.

Причины:

- один процесс API, одна реплика — отдельный scheduler не нужен;
- состояние уже в PostgreSQL (`due_at`, `reminder_sent_at`), поэтому рестарт
  не теряет напоминания;
- меньше зависимостей и кода, проще объяснить на демо.

## Ограничения

- при нескольких репликах API возможна повторная отправка; частично защищает
  `SELECT ... FOR UPDATE SKIP LOCKED`, но отдельного leader election нет;
- нет cron-выражений и сложных правил — только `daily`/`weekly`/`monthly`
  через создание следующего экземпляра при завершении.

## Когда менять

При переходе на несколько реплик или появлении сложных расписаний — заменить
на APScheduler + PostgreSQL job store либо внешний scheduler.
