import { useState } from "react";
import { EventCard } from "../components/EventCard";
import { EventEditor } from "../components/EventEditor";
import { useEvents, type EventRange } from "../hooks/useEvents";

const RANGES: Array<{ value: EventRange; label: string }> = [
  { value: "today", label: "Сегодня" },
  { value: "week", label: "7 дней" },
  { value: "upcoming", label: "30 дней" },
  { value: "all", label: "Все" },
];

export function TimelinePage({ refreshKey }: { refreshKey: number }) {
  const [range, setRange] = useState<EventRange>("upcoming");
  const [showEditor, setShowEditor] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const { events, loading, error, create, complete, remove } = useEvents(
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
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Не удалось удалить");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Таймлайн</h1>
          <p className="hint">Задачи, встречи и напоминания</p>
        </div>
        <button
          className="button"
          type="button"
          onClick={() => setShowEditor((value) => !value)}
        >
          {showEditor ? "Скрыть форму" : "Новое событие"}
        </button>
      </header>

      {showEditor && (
        <EventEditor onCreate={create} onClose={() => setShowEditor(false)} />
      )}

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

      {(error || actionError) && <p className="form-error">{actionError ?? error}</p>}
      {loading && <p className="hint">Загрузка...</p>}
      {!loading && events.length === 0 && (
        <p className="empty-state">В этом периоде событий нет.</p>
      )}

      <div className="event-list">
        {events.map((event) => (
          <EventCard
            key={event.id}
            event={event}
            busy={busyId === event.id}
            onComplete={(id) => void handleComplete(id)}
            onDelete={(id) => void handleDelete(id)}
          />
        ))}
      </div>
    </section>
  );
}
