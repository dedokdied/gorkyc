import type { ChatEntry } from "../hooks/useChat";

const ACTION_LABELS: Record<string, string> = {
  create_event: "создано",
  update_event: "обновлено",
  delete_event: "удалено",
  complete_event: "выполнено",
};

interface Props {
  entry: ChatEntry;
  onSpeak?: (text: string) => void;
}

// The model is asked not to use markdown, but free providers still slip in
// «**жирный**» and headings. Render them as plain text instead of asterisks.
function plainText(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/^#{1,6}\s+/gm, "");
}

export function ChatMessage({ entry, onSpeak }: Props) {
  const label = entry.action?.name ? ACTION_LABELS[entry.action.name] : null;
  const isUser = entry.role === "user";

  return (
    <article className={`message message--${entry.role}`}>
      <div className="message__meta">
        <span className="message__avatar" aria-hidden="true">
          {isUser ? ">" : "■"}
        </span>
        <span>{isUser ? (entry.voice ? "вы, голос" : "вы") : "ЗапишИИ"}</span>
        {label && entry.action?.status === "done" && (
          <span className="message__action">{label}</span>
        )}
        {!isUser && onSpeak && (
          <button
            type="button"
            className="message__speak"
            onClick={() => onSpeak(entry.text)}
            aria-label="Озвучить ответ"
            title="Озвучить ответ"
          >
            ▶
          </button>
        )}
      </div>
      <p>{plainText(entry.text)}</p>
    </article>
  );
}
