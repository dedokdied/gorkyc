# Docs

Документация проекта. Владельцы — оба участника.

```
docs/
├── README.md
├── tz-requests.md      # все запросы из ТЗ и ожидаемое поведение
├── api/
│   └── README.md        # контракт API, DTO, ошибки
└── decisions/
    ├── 0001-architecture.md  # Telegram MVP → web на общем backend
    ├── 0002-free-local-stack.md  # локальный fallback LLM/STT
    ├── 0003-api-first-models.md  # API-first для LLM/STT
    └── 0004-vector-search-deferred.md  # pgvector отложен
```

## Что здесь держать

- Контракт API и примеры запросов/ответов.
- ADR: почему Telegram MVP, общий backend, FastAPI, PostgreSQL, pgvector,
  `pending_actions`, `time_expression`.
- Сценарий демо: 10–20 фраз и ожидаемое поведение.
- Чек-лист приёмки 4 обязательных сценариев в Telegram, затем в вебе.
- Инструкцию по запуску и деплою (дублируется в корневом README).

## ADR: шаблон

```md
# 0001. Название решения

## Контекст
Что требовалось и какие были ограничения.

## Решение
Что выбрали.

## Последствия
Плюсы, минусы, что придётся поддерживать.
```

## Правило

Контракт в `docs/api/README.md` — источник правды для frontend и backend.
Изменение сначала обсуждается, потом фиксируется здесь, потом попадает в код.
