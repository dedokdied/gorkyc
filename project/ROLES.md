# Роли и рабочий контракт

Два участника, две вертикальные зоны. Работаем по OpenClaw-плану из `PLAN.md`.
Правило №1: не редактируем чужую зону без сообщения. Любое изменение контракта —
сначала в `docs/tools.md`, потом в коде.

## Кто есть кто

| | Участник A | Участник B |
|---|---|---|
| **Роль** | Plugin / Domain & Data | OpenClaw Runtime / Skill & Delivery |
| **Главный результат** | Плагин, домен, БД, даты, поиск | Gateway, каналы, skill, голос, automations, деплой |
| **Не делает** | Каналы, `SKILL.md`, деплой | Схему БД, SQL, доменные сервисы, tool-схемы |

## Кто что делает

| Зона | A | B |
|---|---|---|
| OpenClaw Gateway, модели, fallback | — | настраивает |
| Telegram / Control UI / STT / TTS | — | настраивает |
| `openclaw.plugin.json`, manifest, configSchema | владелец | не меняет |
| Tools и TypeBox-схемы | владелец | не меняет |
| `services/`, `repositories/`, `db/`, миграции | владелец | не меняет |
| `pending_actions`, `last_entity_id` | владелец | использует через tools |
| `DatetimeParser`, поиск, импорт CSV | владелец | не меняет |
| `SKILL.md`, промпты, сценарии уточнений | даёт контракт tools | владелец |
| Маппинг `peer_id → user_id` | хранит и валидирует | передаёт trusted-контекст |
| Reminder automations | контракт и `metadata` | создаёт/отменяет job |
| Docker Compose, Postgres | требования к БД | владелец compose |
| Деплой и демо-ссылка | — | владелец |
| E2E и демо-сценарий | домен/поиск | владелец |
| README и `docs/demo.md` | разделы домена | владелец |

## Владение файлами

| Папка / файл | Владелец |
|---|---|
| `plugin/openclaw.plugin.json`, `package.json`, `src/index.ts` | A |
| `plugin/src/{tools,services,repositories,db,schemas}/` | A |
| `plugin/src/integrations/embeddings*` | A |
| `plugin/src/integrations/openclaw*`, `reminders*` | B |
| `plugin/tests/{unit,integration}/` | A |
| `skills/` | B |
| `openclaw/` (config, workspace) | B |
| `infra/docker/` | B (A даёт env и команду миграций) |
| `infra/deploy/` | B |
| `scripts/import-csv.ts`, `scripts/eval-search.ts` | A |
| `scripts/e2e/` | B |
| `docs/tools.md` | A |
| `docs/demo.md`, `README.md` | B |
| `docs/decisions/`, `project/PLAN.md` | вместе |

## Контракт tools — фиксируем в первый час

Минимальный набор:

```text
create_event
update_event
complete_event
delete_event
list_events
search_events
get_current_datetime
```

Единый ответ tool:

```json
{
  "status": "done | needs_clarification | error",
  "entity": null,
  "reply": "короткий текст для пользователя",
  "missing": ["starts_at"],
  "pending_action_id": "uuid или null",
  "clarification": "Во сколько?",
  "error_code": null
}
```

Правила:

- `user_id`, `session_key`, `source` берутся из trusted-контекста OpenClaw, **не из аргументов LLM**.
- LLM передаёт `time_expression` / `duration_expression`, а не готовые даты.
- При нехватке слота tool сохраняет `pending_action` и возвращает `needs_clarification`.
- Напоминание: B создаёт automation, A хранит `automation_id` в `events.metadata`.
- Ошибки — кодами, без stack trace и SQL в ответе модели.

## Интерфейс напоминаний

A вызывает интерфейс, B реализует его через OpenClaw:

```ts
interface ReminderScheduler {
  schedule(input: {
    userId: string;
    sessionKey: string;
    fireAt: string;
    text: string;
  }): Promise<{ automationId: string }>;
  cancel(automationId: string): Promise<void>;
}
```

## Первый час — вместе

- Зафиксировать версию OpenClaw и Node; записать в README.
- Согласовать `docs/tools.md`: имена, аргументы, ответы, ошибки.
- Определить demo-user и маппинг `peer_id`.
- A: manifest + stub одного tool + схема БД.
- B: OpenClaw + Telegram + модель + установка stub-плагина + черновик `SKILL.md`.

## Правила, чтобы не мешать

1. A работает в `feat/plugin-*`, B — в `feat/openclaw-*`.
2. Один активный PR на человека; общие файлы — отдельным маленьким PR.
3. Сначала заглушка/интерфейс, потом реализация — второй не ждёт.
4. Моки обязательны: A тестирует домен без OpenClaw, B тестирует tool через stub.
5. Контракт меняем только через `docs/tools.md` и сообщение в чат.
6. Секреты и токены — только в env/secrets, никогда в git.
7. Версию OpenClaw не обновляем до сдачи.
8. Синк на старте и в конце дня: 15 минут, только блокеры и изменения контракта.

## Definition of Done

- A: tools валидируются, миграции применяются, даты и поиск покрыты тестами, seed из CSV работает.
- B: Gateway и Telegram стабильны, голос работает, reminder срабатывает, skill ведёт уточнения, деплой открывается.
- Вместе: 4 обязательных сценария end-to-end, данные сохраняются после перезапуска, README поднимает проект с нуля, демо-ссылка живая.
