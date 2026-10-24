# Telegram bot (MVP)

Тонкий клиент к backend. Бот не содержит SQL и бизнес-логики: он принимает
текст/голос, вызывает `/api/v1/chat` или `/api/v1/voice` и показывает ответ.

## Зона B

- `handlers/start.py` — регистрация и первый экран.
- `handlers/onboarding.py` — меню «Начать / Примеры / Сделать задачу / Планы».
- `handlers/text.py` — текст → `/chat` или ответ на активное уточнение.
- `handlers/voice.py` — голосовое → `/voice`.
- `identity.py` — Telegram-аккаунт (`from_user.id`) вместо `chat.id`.
- `api_client.py` — HTTP-клиент и заголовки `X-Telegram-Id`,
  `X-Telegram-Username`, `X-Bot-Secret`.
- `keyboards.py` — inline-кнопки онбординга и уточнений.
- `config.py` — токен, backend URL, таймзона.

## Что уже есть (этапы 0–3)

- `/start` с онбордингом: «Начать» / «Примеры», затем «Сделать задачу» /
  «Мои планы».
- `/help`, `/cancel`.
- Текст → `/chat`; если бот ждёт уточнение, ответ идёт в
  `/clarifications/{id}/answer`.
- `/today`, `/tomorrow`, `/week` — список событий.
- `/search договор` — поиск по событиям.
- Голосовое/аудио → `/voice`, бот показывает расшифровку и ответ.
- Данные разделены по Telegram-аккаунту, а не по чату: в группе у каждого
  участника свои события.
- Ассистент помнит последние 4 сообщения диалога.
- Inline-кнопки для уточнений; LLM не просят нажимать кнопки.
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
