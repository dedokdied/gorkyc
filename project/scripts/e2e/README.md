# E2E

Сценарии проверки Telegram MVP и веба. Владелец — B.

## Telegram MVP

1. `/start` → бот отвечает и создаёт пользователя.
2. «Напомни завтра в 10 позвонить Ивану» → напоминание создано.
3. «Поставь встречу с Иваном завтра» → бот спрашивает время.
4. «В 15:00» → встреча создана.
5. «Что у меня завтра?» → список.
6. «Найди задачи про договор» → поиск.
7. Голосовое сообщение с той же фразой.
8. Перезапуск backend → данные на месте.
9. Напоминание приходит в указанное время.

## Автоматическая проверка API

Скрипт проверяет health и сценарии 2–6 через живой backend:

```bash
python scripts/e2e/smoke.py
```

Если API запущен не на localhost:

```bash
python scripts/e2e/smoke.py --base-url https://api.example.com/api/v1
```

Для проверки голоса добавь файл:

```bash
python scripts/e2e/smoke.py --voice-file samples/voice.ogg
```

Требуется `httpx` и доступ к API. Скрипт авторизуется как Telegram-бот:
`X-Telegram-Id` + `X-Bot-Secret` (по умолчанию `1` и `change-me`). Для
защищённого контура задай актуальный `BOT_INTERNAL_SECRET`.

## Web

Browser-тесты лежат в `frontend/e2e/web.spec.ts` (Playwright). Нужны
запущенный backend с PostgreSQL и установленный frontend:

```bash
cd project/frontend
npm ci
npm run e2e
```

Playwright сам поднимает Vite dev server на `127.0.0.1:5173`; backend должен
быть доступен на `127.0.0.1:8000` (Vite proxy). Вне CI по умолчанию
используется установленный Edge; на Linux/CI — Chromium:

```bash
npx playwright install --with-deps chromium
npm run e2e
```

Переменные:

- `E2E_BASE_URL` — адрес уже запущенного frontend;
- `PLAYWRIGHT_CHANNEL` — например, `msedge` или `chrome`;
- `E2E_RUN_ID` — суффикс demo-user, чтобы прогоны не пересекались.

Покрыто: создание напоминания через чат, уточнение времени, таймлайн
(create/complete), поиск, конвертация выбранной таймзоны и мобильный viewport.
CI запускает тот же набор в job `e2e`.

Ручной чеклист для показа — [`docs/demo.md`](../../docs/demo.md).
