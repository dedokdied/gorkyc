import { useEffect, useRef, useState } from "react";
import { ChatMessage } from "../components/ChatMessage";
import { Clarification } from "../components/Clarification";
import { RecordButton } from "../components/RecordButton";
import { useChat } from "../hooks/useChat";

const EXAMPLES = [
  "Напомни завтра в 10 позвонить Ивану",
  "Встреча с Анной в пятницу в 15:00",
  "Что у меня на неделе?",
  "Найди записи про договор",
];

export function ChatPage({
  onEventChanged,
  timezone,
}: {
  onEventChanged: () => void;
  timezone?: string;
}) {
  const {
    messages,
    clarification,
    loading,
    error,
    send,
    answer,
    sendAudio,
    clear,
  } = useChat(onEventChanged, timezone);
  const [text, setText] = useState("");
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const container = messagesRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, clarification]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim() || loading) {
      return;
    }
    if (clarification) {
      void answer(text);
    } else {
      void send(text);
    }
    setText("");
  }

  function pickExample(example: string) {
    setText(example);
    inputRef.current?.focus();
  }

  return (
    <section className="page page--chat">
      <header className="page-head">
        <div>
          <p className="kicker">Диалог / 01</p>
          <h1>Ассистент</h1>
          <p className="hint">Текст или голос — как удобнее. Я разберусь с деталями.</p>
        </div>
        <span className="live-pill">
          <span className="status-dot" />
          {loading ? "слушаю" : "готов"}
        </span>
      </header>

      <div className="chat-layout">
        <div className="chat">
          <div className="chat__topline">
            <span>ВХОДЯЩИЕ / ASSISTANT</span>
            <span className="chat__topline-right">
              <span>
                {messages.length ? `${messages.length} сообщений` : "новый диалог"}
              </span>
              {messages.length > 0 && (
                <button
                  className="chat__clear"
                  type="button"
                  onClick={() => void clear()}
                  disabled={loading}
                >
                  Очистить чат
                </button>
              )}
            </span>
          </div>

          <div className="chat__messages" ref={messagesRef}>
            {messages.length === 0 && (
              <div className="empty-state empty-state--chat">
                <p className="empty-state__index">00 / 04</p>
                <h2>Что планируем?</h2>
                <p>
                  Напишите задачу обычными словами. Можно добавить дату, время и
                  детали — я соберу событие сам.
                </p>
                <div className="prompt-list" aria-label="Примеры запросов">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      className="prompt-chip"
                      type="button"
                      onClick={() => pickExample(example)}
                    >
                      <span aria-hidden="true">↗</span>
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((entry) => (
              <ChatMessage key={entry.id} entry={entry} />
            ))}
            {loading && (
              <p className="chat__typing">
                <span className="status-dot" /> ассистент печатает…
              </p>
            )}
          </div>

          {clarification && (
            <Clarification clarification={clarification} onPick={pickExample} />
          )}
          {error && <p className="form-error">{error}</p>}

          <form className="composer" onSubmit={submit}>
            <input
              ref={inputRef}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={
                clarification
                  ? "Ответьте: например, «завтра в 15:00»"
                  : "Например: встреча завтра в 15:00"
              }
              aria-label={clarification ? "Ответ на уточнение" : "Сообщение"}
              disabled={loading}
            />
            <RecordButton disabled={loading} onRecorded={sendAudio} />
            <button className="button button--primary" type="submit" disabled={loading || !text.trim()}>
              {clarification ? "Ответить" : "Отправить"} <span aria-hidden="true">↗</span>
            </button>
          </form>
        </div>

        <aside className="chat-aside">
          <div className="aside-card">
            <p className="aside-card__title">Что умею</p>
            <ol className="ability-list">
              <li>
                <span>01</span> Создавать задачи, встречи и напоминания
              </li>
              <li>
                <span>02</span> Показывать планы за день или неделю
              </li>
              <li>
                <span>03</span> Искать старые записи по смыслу слов
              </li>
              <li>
                <span>04</span> Уточнять время, если его не хватает
              </li>
            </ol>
          </div>
          <p className="aside-note">
            Голосовой ввод работает в браузере. Если микрофон недоступен, просто
            напишите текстом.
          </p>
        </aside>
      </div>
    </section>
  );
}
