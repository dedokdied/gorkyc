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

Автоматического browser-теста пока нет; проверка ручная по
[`docs/demo.md`](../../docs/demo.md). Минимальный smoke:

```bash
cd project/frontend
npm run dev
```

1. `http://localhost:5173` открывается, `/api/v1/healthz` доступен через Vite
   proxy.
2. Demo-пользователь видит только свои события.
3. Чат, таймлайн (create/complete/delete), поиск и голосовой ввод работают.
4. Сборка `npm run build` проходит; мобильная вёрстка не ломается.
