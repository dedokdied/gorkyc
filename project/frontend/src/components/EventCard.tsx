import type { EventItem } from "../types/api";

const TYPE_LABELS: Record<EventItem["type"], string> = {
  task: "Задача",
  meeting: "Встреча",
  reminder: "Напоминание",
};

const TYPE_CODES: Record<EventItem["type"], string> = {
  task: "T",
  meeting: "M",
  reminder: "R",
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
  onEdit?: (event: EventItem) => void;
  busy?: boolean;
  snippet?: string;
  score?: number;
}

export function EventCard({
  event,
  onComplete,
  onDelete,
  onEdit,
  busy = false,
  snippet,
  score,
}: Props) {
  const when = formatWhen(event);

  return (
    <article className={`event-card event-card--${event.type}`}>
      <header className="event-card__header">
        <span className="event-card__type">
          <span className="event-card__code">{TYPE_CODES[event.type]}</span>
          {TYPE_LABELS[event.type]}
        </span>
        <span className={`event-card__status event-card__status--${event.status}`}>
          {STATUS_LABELS[event.status]}
        </span>
      </header>
      <h3>{event.title}</h3>
      <p className="event-card__when">{when ?? "Без даты"}</p>
      {snippet && <p className="event-card__snippet">{snippet}</p>}
      {event.description && <p className="event-card__description">{event.description}</p>}
      {score !== undefined && (
        <p className="event-card__score">
          релевантность <span>{score.toFixed(2)}</span>
        </p>
      )}
      {(onComplete || onDelete || onEdit) && (
        <footer className="event-card__actions">
          {onEdit && (
            <button
              className="button button--small button--ghost"
              type="button"
              disabled={busy}
              onClick={() => onEdit(event)}
            >
              Изменить
            </button>
          )}
          {onComplete && event.status === "planned" && (
            <button
              className="button button--small button--primary"
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
