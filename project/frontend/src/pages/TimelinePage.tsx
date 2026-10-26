import { useState } from "react";
import { EventCard } from "../components/EventCard";
import { EventEditor } from "../components/EventEditor";
import { useEvents, type EventRange } from "../hooks/useEvents";
import type { EventItem } from "../types/api";

const RANGES: Array<{ value: EventRange; label: string }> = [
  { value: "today", label: "Сегодня" },
  { value: "week", label: "7 дней" },
  { value: "upcoming", label: "30 дней" },
  { value: "all", label: "Все" },
];

export function TimelinePage({ refreshKey }: { refreshKey: number }) {
  const [range, setRange] = useState<EventRange>("upcoming");
  const [showEditor, setShowEditor] = useState(false);
  const [editing, setEditing] = useState<EventItem | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const { events, loading, error, create, update, complete, remove } = useEvents(
    range,
    refreshKey,
  );

  async function handleComplete(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      await complete(id);
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Не удалось выполнить");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Удалить событие?")) {
      return;
    }
    setBusyId(id);
    setActionError(null);
    try {
      await remove(id);
      if (editing?.id === id) {
        setEditing(null);
        setShowEditor(false);
      }
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Не удалось удалить");
    } finally {
      setBusyId(null);
    }
  }

  function openCreate() {
    setEditing(null);
    setShowEditor(true);
  }

  function openEdit(event: EventItem) {
    setEditing(event);
    setShowEditor(true);
  }

  function closeEditor() {
    setShowEditor(false);
    setEditing(null);
  }

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="kicker">Планы / 02</p>
          <h1>Таймлайн</h1>
          <p className="hint">Задачи, встречи и напоминания — в одном ритме.</p>
        </div>
        <div className="page-head__actions">
          <span className="count-label">
            {loading ? "—" : String(events.length).padStart(2, "0")}
            <small>событий</small>
          </span>
          <button
            className="button button--primary"
            type="button"
            onClick={() => (showEditor ? closeEditor() : openCreate())}
          >
            {showEditor ? "Скрыть форму" : "Новое событие"}
          </button>
        </div>
      </header>

      {showEditor && (
        <EventEditor
          event={editing}
          onCreate={create}
          onUpdate={update}
          onClose={closeEditor}
        />
      )}

      <div className="timeline-bar">
        <div className="tabs" role="tablist" aria-label="Период">
          {RANGES.map((item) => (
            <button
              key={item.value}
              type="button"
              role="tab"
              aria-selected={range === item.value}
              className={`tab ${range === item.value ? "tab--active" : ""}`}
              onClick={() => setRange(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span className="timeline-bar__hint">время — в вашем часовом поясе</span>
      </div>

      {(error || actionError) && <p className="form-error">{actionError ?? error}</p>}
      {loading && <p className="hint">Загрузка…</p>}
      {!loading && events.length === 0 && (
        <div className="empty-state">
          <p className="empty-state__index">00 / 00</p>
          <h2>Пока пусто.</h2>
          <p>Создайте первое событие или попросите ассистента сделать это за вас.</p>
          <button className="button button--ghost" type="button" onClick={openCreate}>
            Создать событие
          </button>
        </div>
      )}

      <div className="event-list">
        {events.map((event) => (
          <EventCard
            key={event.id}
            event={event}
            busy={busyId === event.id}
            onComplete={(id) => void handleComplete(id)}
            onDelete={(id) => void handleDelete(id)}
            onEdit={openEdit}
          />
        ))}
      </div>
    </section>
  );
}
