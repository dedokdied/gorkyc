# ADR 0003: API-first для LLM и STT

- Статус: принято
- Дата: 2026-10-22
- Владелец: B
- Область: LLM, STT
- Заменяет: ADR 0002 в части LLM и STT

## Решение

Сначала используем внешние API, а локальные модели держим как резерв.
Оба интеграционных слоя работают через OpenAI-compatible протокол,
поэтому провайдера можно сменить только через `.env`.

| Компонент | Основной режим | Резерв | Статус |
|---|---|---|---|
| LLM | API `/chat/completions` | `RuleBasedLLM`; Ollama — отдельный режим | включён |
| STT | API `/audio/transcriptions` | локальный `faster-whisper` | включён |
| TTS | пока нет, `NullTTS` | после MVP | отключён |

API может быть OpenAI, OpenRouter, Groq или другим совместимым сервисом.
Конкретный провайдер и лимиты выбираются при настройке окружения.

## Настройки

```env
LLM_PROVIDER=api
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT=60

STT_PROVIDER=api
STT_API_KEY=

STT_BASE_URL=https://api.openai.com/v1
STT_TIMEOUT=60
STT_LANGUAGE=ru

TTS_PROVIDER=none
```

- `LLM_PROVIDER=api` и `STT_PROVIDER=api` — режим по умолчанию.
- Пустой `LLM_API_KEY` переключает чат на `RuleBasedLLM`.
- Пустой `STT_API_KEY` отключает голос, текстовый чат продолжает работать.
- Ошибка API LLM автоматически уходит в `RuleBasedLLM` через `FallbackLLM`.
- Ошибка STT API возвращает понятную ошибку пользователю, без тихого
  переключения на локальную модель.

## Локальный резерв

Локальные провайдеры остаются в коде и включаются явно:

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_BASE_URL=http://localhost:11434/v1

STT_PROVIDER=faster-whisper
STT_MODEL=small
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
```

Лицензии и ограничения локального стека — в ADR 0002.

## Последствия

- Нужны ключи API и контроль расходов/лимитов.
- Ключи хранятся только в `.env` или secrets хостинга и не коммитятся.
- Без интернета или без ключей остаётся текстовый `RuleBasedLLM`;
  голос в таком режиме недоступен.
- ADR 0002 больше не определяет основной режим LLM/STT.
