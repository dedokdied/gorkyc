# ADR 0002: только бесплатные локальные решения

- Статус: принято
- Дата: 2026-10-22
- Владелец: B
- Область: LLM, STT, TTS, поиск

## Решение

В проекте не используем платные API и сервисы с оплатой за запрос.
Все тяжёлые компоненты работают локально или отключены.

| Компонент | Решение | Лицензия | Статус |
|---|---|---|---|
| STT | `faster-whisper`, модель `small`/`medium`, CPU int8 | код MIT, веса Whisper Apache-2.0 | включён |
| STT-альтернатива | Vosk Russian, `vosk-model-small-ru-0.22` | Apache-2.0 | запасной вариант |
| LLM | Ollama + Qwen2.5 3B/7B | Ollama MIT, Qwen2.5 3B/7B Apache-2.0 | опционально |
| LLM fallback | `RuleBasedLLM` | код проекта | всегда доступен |
| TTS | пока нет, `NullTTS` | — | после MVP |
| Поиск | PostgreSQL FTS `russian` + `pg_trgm` | PostgreSQL License | этап A |
| Telegram | Bot API | бесплатный | включён |

## Почему так

- `faster-whisper` хорошо понимает русскую свободную речь и работает
  без интернета. Модель `small` — компромисс между качеством, RAM и CPU.
- Vosk легче и быстрее, но на свободных фразах ошибается чаще.
  Оставляем как альтернативу для слабого железа.
- Ollama запускает Qwen2.5 локально и не требует API-ключа.
  Если Ollama не запущена или модель недоступна, `FallbackLLM`
  переключается на `RuleBasedLLM`.
- Postgres FTS закрывает поиск по событиям без embeddings и внешних API.
- TTS не входит в MVP: сначала 4 обязательных сценария, потом голоса.

## Что не используем

- OpenAI Whisper API, Groq, Yandex SpeechKit и другие платные STT.
- OpenAI/Anthropic и любые LLM с оплатой за токены.
- Silero TTS и Coqui XTTS — ограничения non-commercial.
- `edge-tts` — неофициальный доступ к сервису Microsoft, риск по ToS.
- Kokoro — Apache-2.0, но русского языка в модели нет.

## Настройки

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_BASE_URL=http://localhost:11434/v1
LLM_TIMEOUT=120

STT_PROVIDER=faster-whisper
STT_MODEL=small
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
STT_LANGUAGE=ru

TTS_PROVIDER=none
```

`LLM_PROVIDER=rule-based` полностью отключает Ollama.
`STT_PROVIDER=none` отключает голос, но текстовый чат продолжает работать.

## Установка локальных моделей

```bash
# STT
pip install faster-whisper

# LLM
ollama pull qwen2.5:3b
```

Модель Whisper `small` занимает примерно 250–500 МБ.
Qwen2.5 3B в квантованном виде — около 2 ГБ RAM.
Точные требования зависят от версии и квантования.

## TTS после MVP

Если понадобится озвучка, бесплатный локальный вариант — Piper:

- движок `OHF-Voice/piper1-gpl` — GPL-3.0;
- голоса `rhasspy/piper-voices` — MIT;
- русские голоса: `irina`, `denis`, `dmitri`, `ruslan`.

GPL-3.0 накладывает ограничения при распространении проекта.
Поэтому TTS не добавляем в MVP и решаем отдельно после приёмки.

## Правила для кода

- В коде нет обязательных API-ключей для LLM/STT/TTS.
- Новый провайдер добавляется только с открытой лицензией и локальным запуском.
- Внешний платный API можно добавить только через новый ADR.
- Если локальная модель не установлена, сервис возвращает понятную ошибку,
  а не пытается молча уйти в платный сервис.
