import type { EventItem } from "../types/api";

function formatDue(event: EventItem): string {
  const value = event.due_at ?? event.starts_at;
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ReminderBanner({
  reminders,
  onDismiss,
}: {
  reminders: EventItem[];
  onDismiss: (id: string) => void;
}) {
  if (reminders.length === 0) {
    return null;
  }

  return (
    <div className="reminder-banner" role="status" aria-live="polite">
      <span className="reminder-banner__mark" aria-hidden="true">
        ●
      </span>
      <div className="reminder-banner__body">
        {reminders.map((reminder) => (
          <div className="reminder-banner__item" key={reminder.id}>
            <span>
              <strong>{reminder.title}</strong>
              {formatDue(reminder) && (
                <span className="reminder-banner__time">{formatDue(reminder)}</span>
              )}
            </span>
            <button
              className="button button--small button--ghost"
              type="button"
              onClick={() => onDismiss(reminder.id)}
            >
              Понятно
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
