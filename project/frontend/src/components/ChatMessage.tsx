import type { ChatEntry } from "../hooks/useChat";

const ACTION_LABELS: Record<string, string> = {
  create_event: "создано",
  update_event: "обновлено",
  delete_event: "удалено",
  complete_event: "выполнено",
};

export function ChatMessage({ entry }: { entry: ChatEntry }) {
  const label = entry.action?.name ? ACTION_LABELS[entry.action.name] : null;
  const isUser = entry.role === "user";

  return (
    <article className={`message message--${entry.role}`}>
      <div className="message__meta">
        <span className="message__avatar" aria-hidden="true">
          {isUser ? ">" : "■"}
        </span>
        <span>{isUser ? (entry.voice ? "вы, голос" : "вы") : "горький"}</span>
        {label && entry.action?.status === "done" && (
          <span className="message__action">{label}</span>
        )}
      </div>
      <p>{entry.text}</p>
    </article>
  );
}
