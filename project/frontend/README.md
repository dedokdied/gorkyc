# Frontend

React + TypeScript + Vite. Владелец — участник B. UI минимальный, но аккуратный:
чат, история, карточки событий, таймлайн, поиск, настройки.

## Структура

```
src/
├── api/
│   ├── client.ts            # fetch/axios, базовый URL, ошибки
│   ├── events.ts            # /events
│   ├── search.ts            # /search
│   └── chat.ts              # /chat, /voice
├── components/
│   ├── RecordButton.tsx     # push-to-talk, запись, отмена
│   ├── ChatMessage.tsx      # сообщение, TTS-кнопка
│   ├── EventCard.tsx        # тип, дата, статус, действия
│   ├── Clarification.tsx    # быстрые ответы на уточнение
│   ├── EventEditor.tsx      # правка распознанных полей
│   └── SearchBar.tsx
├── hooks/
│   ├── useRecorder.ts       # MediaRecorder API
│   ├── useChat.ts           # отправка, SSE, история
│   └── useEvents.ts         # TanStack Query
├── pages/
│   ├── ChatPage.tsx         # главный экран
│   ├── TimelinePage.tsx     # сегодня/завтра/неделя
│   └── SearchPage.tsx       # поиск по старым записям
├── store/
│   └── session.ts           # Zustand: сессия, настройки
└── types/
    └── api.ts               # типы, синхронизированные с docs/api
```

## Mock-режим

Пока backend не готов:

```env
VITE_USE_MOCKS=true
```

Моки лежат в `src/api/mocks.ts` (создать при старте). Они повторяют контракт из
`docs/api/README.md`: события, список, поиск, чат, уточнения. После интеграции
флаг выключается, код UI не меняется.

## UX-требования

- Кнопка записи всегда видна; текстовый ввод доступен как fallback.
- Видна расшифровка; можно отредактировать до отправки.
- После создания показывается карточка с распознанными полями и кнопками
  «Изменить» / «Отменить».
- Уточнения — быстрые кнопки, а не тупиковый вопрос.
- Ответ дублируется текстом, даже если TTS сработал.
- Ошибки сети и LLM понятны пользователю, без stack trace.
- Мобильная вёрстка обязательна: демо часто открывают с телефона.

## Запуск (когда появится код)

```bash
cd project/frontend
npm install
npm run dev
```

Сборка:

```bash
npm run build
```
