import type { EventItem } from "../types/api";

const TYPE_LABELS: Record<EventItem["type"], string> = {
  task: "Задача",
  meeting: "Встреча",
  reminder: "Напоминание",
};

const STATUS_LABELS: Record<EventItem["status"], string> = {
  planned: "Запланировано",
  done: "Выполнено",
  cancelled: "Отменено",
};

function formatWhen(event: EventItem): string | null {
  const value = event.due_at ?? event.starts_at;
  if (!value) {
    return null;
  }
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

interface Props {
  event: EventItem;
  onComplete?: (id: string) => void;
  onDelete?: (id: string) => void;
  busy?: boolean;
  snippet?: string;
  score?: number;
}

export function EventCard({
  event,
  onComplete,
  onDelete,
  busy = false,
  snippet,
  score,
}: Props) {
  const when = formatWhen(event);

  return (
    <article className={`event-card event-card--${event.type}`}>
      <header className="event-card__header">
        <span className="event-card__type">{TYPE_LABELS[event.type]}</span>
        <span className={`event-card__status event-card__status--${event.status}`}>
          {STATUS_LABELS[event.status]}
        </span>
      </header>
      <h3>{event.title}</h3>
      {when && <p className="event-card__when">{when}</p>}
      {!when && <p className="event-card__when">Без даты</p>}
      {snippet && <p className="event-card__snippet">{snippet}</p>}
      {event.description && <p className="event-card__description">{event.description}</p>}
      {score !== undefined && (
        <p className="event-card__score">Релевантность: {score.toFixed(2)}</p>
      )}
      {(onComplete || onDelete) && (
        <footer className="event-card__actions">
          {onComplete && event.status === "planned" && (
            <button
              className="button button--small"
              type="button"
              disabled={busy}
              onClick={() => onComplete(event.id)}
            >
              Выполнить
            </button>
          )}
          {onDelete && (
            <button
              className="button button--small button--ghost"
              type="button"
              disabled={busy}
              onClick={() => onDelete(event.id)}
            >
              Удалить
            </button>
          )}
        </footer>
      )}
    </article>
  );
}
