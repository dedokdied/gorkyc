# Scripts

Вспомогательные скрипты. Запускать из `project/` с активированным venv backend
и настроенным `DATABASE_URL`.

| Скрипт | Назначение |
|---|---|
| `import_csv.py` | импорт `voice_assistant_events_1000_*.csv` в БД |
| `seed_demo.py` | demo-user и базовые события для показа |
| `eval_search.py` | заготовка golden-set для оценки поиска |
| `eval_nlu.py` | заготовка набора фраз для оценки NLU |
| `deploy.sh` | сборка и деплой (не хранить секреты) |
| `e2e/` | API smoke и Playwright browser-тесты |

## Импорт CSV

```bash
python scripts/import_csv.py --dry-run
python scripts/import_csv.py --user demo
python scripts/import_csv.py --csv data/my_events.csv --user demo
```

`import_csv.py`:

- читает UTF-8 с BOM;
- классифицирует `встреча/созвон/планёрка/демо` → `meeting`,
  `напомнить` → `reminder`, иначе `task`;
- пишет `source="import"`;
- по умолчанию дедуплицирует по `(title, datetime)` и не создаёт дубли при
  повторном запуске;
- импортирует встречи по 15 минут, чтобы соседние слоты корпуса не
  пересекались; длительность меняется через `--meeting-duration`;
- принимает даты 2024–2027 и время из файла (08:00–20:45).

CSV ищется в `project/data/`, затем в корне репозитория. Файл датасета — не
«боевые» данные пользователя, а seed/корпус для проверки поиска.

## Seed демо

```bash
python scripts/seed_demo.py --user demo
```

Создаёт напоминание, встречу, задачи и одно выполненное событие относительно
текущей даты. Повторный запуск идемпотентен по названию события.

## E2E

- `e2e/smoke.py` — API smoke с Telegram-auth.
- `frontend/e2e/web.spec.ts` — Playwright: чат, уточнение, таймлайн, поиск,
  timezone и мобильная вёрстка.

Подробности — в [`e2e/README.md`](e2e/README.md).

## Оценка качества

`eval_search.py` и `eval_nlu.py` — заготовки для расширенной оценки на
golden-set. В демо и CI они не запускаются; базовые сценарии покрыты
backend-тестами и Playwright.
