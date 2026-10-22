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

## Команды

- `/start` — приветствие и регистрация.
- `/today`, `/tomorrow`, `/week` — список событий.
- `/search` — поиск по старым записям.
- `/settings` — таймзона и TTS.
- `/help` — подсказка.

## Запуск

```bash
cd project/telegram_bot
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m app.main
```

Переменные:

```env
TELEGRAM_BOT_TOKEN=
BACKEND_URL=http://localhost:8000/api/v1
BOT_INTERNAL_SECRET=change-me
```

MVP работает через long polling. Webhook не нужен.
