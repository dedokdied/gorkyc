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

## Что уже есть (этапы 0–3)

- `/start`, `/help`.
- Текст → `/chat`.
- `/today`, `/tomorrow`, `/week` — список событий.
- `/search договор` — поиск по событиям.
- Голосовое/аудио → `/voice`, бот показывает расшифровку и ответ.
- Даты считаются в таймзоне пользователя, время показывается локально.
- Inline-кнопки для уточнений.
- Ошибки backend показываются пользователю без stack trace.
- Mock-режим: бот, список событий, поиск и голос работают без backend.

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

В mock-режиме `/today`, `/tomorrow`, `/week` показывают тестовые события,
`/search` ищет по ним, а голосовое возвращает тестовую расшифровку.
Например:

```text
Сегодня:

— Встреча: Встреча с Иваном (22.10 15:00)
```

MVP работает через long polling. Webhook не нужен.

## Тесты

```bash
.venv\Scripts\python.exe -m pytest -q
```
