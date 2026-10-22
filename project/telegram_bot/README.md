# Telegram bot (MVP)

Тонкий клиент к backend. Бот не содержит SQL и бизнес-логики: он принимает
текст/голос, вызывает `/api/v1/chat` или `/api/v1/voice` и показывает ответ.

## Зона B

- `handlers/start.py` — регистрация, таймзона.
- `handlers/text.py` — текст → `/chat`.
- `handlers/voice.py` — голосовое → `/voice`.
- `api_client.py` — HTTP-клиент и заголовки `X-Telegram-Id`, `X-Bot-Secret`.
- `keyboards.py` — inline-кнопки уточнений.
- `config.py` — токен, backend URL, таймзона.

## Что уже есть (этап 0)

- `/start`, `/help`.
- Текст → `/chat`.
- Inline-кнопки для уточнений.
- Ошибки backend показываются пользователю без stack trace.
- Mock-режим: бот работает без backend.

`/today`, `/tomorrow`, `/week`, `/search` и голос — следующие этапы.

## Запуск

```bash
cd project/telegram_bot
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m app.main
```

Переменные берутся из `project/.env` или `project/telegram_bot/.env`:

```env
TELEGRAM_BOT_TOKEN=
BACKEND_URL=http://localhost:8000/api/v1
BOT_INTERNAL_SECRET=change-me
BOT_MOCK_MODE=false
```

Для проверки без backend:

```env
BOT_MOCK_MODE=true
```

MVP работает через long polling. Webhook не нужен.

## Тесты

```bash
.venv\Scripts\python.exe -m pytest -q
```
