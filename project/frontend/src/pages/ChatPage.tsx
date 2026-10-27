import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChatMessage } from "../components/ChatMessage";
import { Clarification } from "../components/Clarification";
import { VoiceCall } from "../components/VoiceCall";
import { VoiceInputButton } from "../components/VoiceInputButton";
import { useChat } from "../hooks/useChat";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";
import type { AssistantMode } from "../store/mode";

const EXAMPLES = [
  "Напомни завтра в 10 позвонить Ивану",
  "Встреча с Анной в пятницу в 15:00",
  "Что у меня на неделе?",
  "Найди записи про договор",
];

export function ChatPage({
  onEventChanged,
  timezone,
  mode,
  onModeChange,
  onVoiceCallChange,
}: {
  onEventChanged: () => void;
  timezone?: string;
  mode: AssistantMode;
  onModeChange: (mode: AssistantMode) => void;
  onVoiceCallChange: (open: boolean) => void;
}) {
  const {
    messages,
    clarification,
    loading,
    error,
    send,
    answer,
    clear,
  } = useChat(onEventChanged, timezone);
  const [text, setText] = useState("");
  const [callOpen, setCallOpen] = useState(false);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const openedForModeRef = useRef(false);
  const { speak, speaking, cancel } = useSpeechSynthesis();

  useEffect(() => {
    const container = messagesRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, clarification]);

  useEffect(() => {
    if (mode === "voice" && !openedForModeRef.current) {
      openedForModeRef.current = true;
      setCallOpen(true);
    }
    if (mode === "text") {
      openedForModeRef.current = false;
    }
  }, [mode]);

  useEffect(() => {
    if (mode === "text") {
      cancel();
    }
  }, [cancel, mode]);

  useEffect(() => {
    const open = callOpen && mode === "voice";
    onVoiceCallChange(open);
    return () => {
      if (open) {
        onVoiceCallChange(false);
      }
    };
  }, [callOpen, mode, onVoiceCallChange]);

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

  function applyTranscript(next: string) {
    setText(next);
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }

  function closeCall() {
    setCallOpen(false);
    onModeChange("text");
  }

  function voiceTurn(value: string) {
    return clarification ? answer(value) : send(value);
  }

  return (
    <section className="page page--chat">
      <header className="page-head">
        <div>
          <p className="kicker">Диалог / 01</p>
          <h1>Ассистент</h1>
          <p className="hint">Текст или голос — как удобнее. Я разберусь с деталями.</p>
        </div>
        <div className="page-head__actions">
          <div className="mode-switch" role="group" aria-label="Режим общения">
            <button
              type="button"
              className={`mode-switch__item ${mode === "text" ? "mode-switch__item--active" : ""}`}
              aria-pressed={mode === "text"}
              onClick={() => onModeChange("text")}
            >
              Текст
            </button>
            <button
              type="button"
              className={`mode-switch__item ${mode === "voice" ? "mode-switch__item--active" : ""}`}
              aria-pressed={mode === "voice"}
              onClick={() => onModeChange("voice")}
            >
              <span className="mode-switch__dot" aria-hidden="true" />
              Звонок
            </button>
          </div>
          <span className="live-pill">
            <span className="status-dot" />
            {loading ? "слушаю" : speaking ? "говорю" : "готов"}
          </span>
        </div>
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
                  Напишите задачу обычными словами или надиктуйте её микрофоном.
                  Можно добавить дату, время и детали — я соберу событие сам.
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
              <ChatMessage
                key={entry.id}
                entry={entry}
                onSpeak={(value) => void speak(value)}
              />
            ))}
            {loading && (
              <p className="chat__typing">
                <span className="status-dot" /> ассистент печатает…
              </p>
            )}
            {speaking && (
              <button type="button" className="chat__speaking" onClick={cancel}>
                <span className="status-dot" /> ЗапишИИ говорит · остановить
              </button>
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
            <VoiceInputButton disabled={loading} value={text} onChange={applyTranscript} />
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
                <span>04</span> Слушать голос и отвечать голосом
              </li>
            </ol>
          </div>
        </aside>
      </div>

      {createPortal(
        <VoiceCall
          open={callOpen && mode === "voice"}
          greeting={clarification?.question ?? null}
          onTurn={voiceTurn}
          onClose={closeCall}
        />,
        document.body,
      )}
    </section>
  );
}
