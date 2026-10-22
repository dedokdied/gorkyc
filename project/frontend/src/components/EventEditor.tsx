import { useState } from "react";
import type { EventCreate, EventType } from "../types/api";
import { zonedDateTimeToIso } from "../utils/timezone";

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

function defaultLocalTime(): string {
  const date = new Date(Date.now() + 3_600_000);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

interface Props {
  onCreate: (payload: EventCreate) => Promise<unknown>;
  onClose: () => void;
}

export function EventEditor({ onCreate, onClose }: Props) {
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [type, setType] = useState<EventType>("task");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [when, setWhen] = useState(defaultLocalTime);
  const [timezone, setTimezone] = useState(
    TIMEZONES.includes(browserTimezone) ? browserTimezone : "Europe/Moscow",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      setError("Введите название");
      return;
    }

    const payload: EventCreate = {
      type,
      title: title.trim(),
      timezone,
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
      await onCreate(payload);
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось создать событие");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel event-editor" onSubmit={(event) => void submit(event)}>
      <div className="panel__header">
        <h2>Новое событие</h2>
        <button type="button" className="button button--small button--ghost" onClick={onClose}>
          Закрыть
        </button>
      </div>

      <div className="field-row">
        <label>
          Тип
          <select value={type} onChange={(event) => setType(event.target.value as EventType)}>
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
            onChange={(event) => setWhen(event.target.value)}
            required={type !== "task"}
          />
        </label>
      </div>

      <label>
        Название
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={300}
          required
          placeholder="Позвонить Ивану"
        />
      </label>

      <label>
        Описание
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          placeholder="Детали, ссылка, заметки"
        />
      </label>

      <label>
        Часовой пояс
        <select value={timezone} onChange={(event) => setTimezone(event.target.value)}>
          {TIMEZONES.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
      </label>

      {type === "meeting" && <p className="hint">Встреча создаётся на 60 минут.</p>}
      {error && <p className="form-error">{error}</p>}

      <button className="button" type="submit" disabled={busy}>
        {busy ? "Создание..." : "Создать"}
      </button>
    </form>
  );
}
