import { useEffect, useRef, useState } from "react";
import { ChatMessage } from "../components/ChatMessage";
import { Clarification } from "../components/Clarification";
import { RecordButton } from "../components/RecordButton";
import { useChat } from "../hooks/useChat";

export function ChatPage({ onEventChanged }: { onEventChanged: () => void }) {
  const { messages, clarification, loading, error, send, answer, sendAudio } =
    useChat(onEventChanged);
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, clarification]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim() || loading) {
      return;
    }
    void send(text);
    setText("");
  }

  return (
    <section className="page page--chat">
      <div className="chat">
        <div className="chat__messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <h2>Чем помочь?</h2>
              <p>
                Напишите или запишите голосом: «Напомни завтра в 10 позвонить Ивану»,
                «Встреча с Анной в пятницу в 15:00», «Что у меня на неделе?».
              </p>
            </div>
          )}
          {messages.map((entry) => (
            <ChatMessage key={entry.id} entry={entry} />
          ))}
          {loading && <p className="chat__typing">Ассистент печатает...</p>}
          <div ref={endRef} />
        </div>

        {clarification && (
          <Clarification
            clarification={clarification}
            disabled={loading}
            onAnswer={(value) => void answer(value)}
          />
        )}
        {error && <p className="form-error">{error}</p>}

        <form className="composer" onSubmit={submit}>
          <input
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Сообщение"
            aria-label="Сообщение"
            disabled={loading}
          />
          <RecordButton disabled={loading} onRecorded={sendAudio} />
          <button className="button" type="submit" disabled={loading || !text.trim()}>
            Отправить
          </button>
        </form>
      </div>
    </section>
  );
}
