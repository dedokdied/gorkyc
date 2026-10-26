import { useState } from "react";
import type { EventCreate, EventItem, EventPatch, EventType } from "../types/api";
import { isoToZonedDateTime, zonedDateTimeToIso } from "../utils/timezone";

const TIMEZONES = [
  "Europe/Moscow",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Almaty",
  "Asia/Tbilisi",
  "Asia/Dubai",
  "America/New_York",
  "UTC",
];

const RECURRENCE_OPTIONS = [
  { value: "", label: "Не повторять" },
  { value: "daily", label: "Каждый день" },
  { value: "weekly", label: "Каждую неделю" },
  { value: "monthly", label: "Каждый месяц" },
];

function defaultLocalTime(): string {
  const date = new Date(Date.now() + 3_600_000);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

interface Props {
  event?: EventItem | null;
  onCreate: (payload: EventCreate) => Promise<unknown>;
  onUpdate?: (id: string, payload: EventPatch) => Promise<unknown>;
  onClose: () => void;
}

export function EventEditor({ event, onCreate, onUpdate, onClose }: Props) {
  const editing = Boolean(event);
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const initialTimezone = event?.timezone ?? (
    TIMEZONES.includes(browserTimezone) ? browserTimezone : "Europe/Moscow"
  );
  const [type, setType] = useState<EventType>(event?.type ?? "task");
  const [title, setTitle] = useState(event?.title ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  const [when, setWhen] = useState(
    event
      ? isoToZonedDateTime(event.due_at ?? event.starts_at, initialTimezone)
      : defaultLocalTime(),
  );
  const [timezone, setTimezone] = useState(initialTimezone);
  const [recurrence, setRecurrence] = useState(event?.recurrence ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(formEvent: React.FormEvent) {
    formEvent.preventDefault();
    if (!title.trim()) {
      setError("Введите название");
      return;
    }

    const payload: EventCreate = {
      type,
      title: title.trim(),
      timezone,
      recurrence: recurrence || null,
    };
    if (description.trim()) {
      payload.description = description.trim();
    }
    if (when) {
      const iso = zonedDateTimeToIso(when, timezone);
      if (type === "meeting") {
        payload.starts_at = iso;
        payload.duration_minutes = 60;
      } else {
        payload.due_at = iso;
      }
    }

    setBusy(true);
    setError(null);
    try {
      if (editing && event && onUpdate) {
        const patch: EventPatch = {
          title: payload.title,
          description: payload.description ?? null,
          timezone: payload.timezone,
          recurrence: payload.recurrence ?? null,
        };
        if (payload.starts_at) {
          patch.starts_at = payload.starts_at;
          patch.duration_minutes = 60;
        }
        if (payload.due_at) {
          patch.due_at = payload.due_at;
        }
        await onUpdate(event.id, patch);
      } else {
        await onCreate(payload);
      }
      onClose();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : editing
            ? "Не удалось сохранить событие"
            : "Не удалось создать событие",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel event-editor" onSubmit={(event_) => void submit(event_)}>
      <div className="panel__header">
        <div>
          <p className="kicker">Ручной ввод / {editing ? "правка" : "новое"}</p>
          <h2>{editing ? "Редактировать событие" : "Новое событие"}</h2>
        </div>
        <button type="button" className="button button--small button--ghost" onClick={onClose}>
          Закрыть
        </button>
      </div>

      <div className="field-row">
        <label>
          Тип
          <select
            value={type}
            disabled={editing}
            onChange={(e) => setType(e.target.value as EventType)}
          >
            <option value="task">Задача</option>
            <option value="reminder">Напоминание</option>
            <option value="meeting">Встреча</option>
          </select>
        </label>
        <label>
          Когда
          <input
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required={type !== "task"}
          />
        </label>
      </div>

      <label>
        Название
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={300}
          required
          placeholder="Позвонить Ивану"
        />
      </label>

      <label>
        Описание
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="Детали, ссылка, заметки"
        />
      </label>

      <div className="field-row">
        <label>
          Часовой пояс
          <select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            {TIMEZONES.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
        </label>
        <label>
          Повтор
          <select value={recurrence} onChange={(e) => setRecurrence(e.target.value)}>
            {RECURRENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {type === "meeting" && <p className="hint">Встреча создаётся на 60 минут.</p>}
      {recurrence && (
        <p className="hint">Следующий экземпляр появится после отметки «Выполнить».</p>
      )}
      {error && <p className="form-error">{error}</p>}

      <button className="button button--primary" type="submit" disabled={busy}>
        {busy ? "Сохраняю..." : editing ? "Сохранить" : "Создать событие"}
      </button>
    </form>
  );
}
