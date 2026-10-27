import { useMemo, useState } from "react";
import { EventCalendar, eventDayKey, formatDayLabel } from "../components/EventCalendar";
import { EventCard } from "../components/EventCard";
import { EventEditor } from "../components/EventEditor";
import {
  useEvents,
  useMonthEvents,
  type EventRange,
} from "../hooks/useEvents";
import type { EventItem } from "../types/api";

const RANGES: Array<{ value: EventRange; label: string }> = [
  { value: "today", label: "Сегодня" },
  { value: "week", label: "7 дней" },
  { value: "upcoming", label: "30 дней" },
  { value: "all", label: "Все" },
];

type View = "active" | "done";

export function TimelinePage({ refreshKey }: { refreshKey: number }) {
  const [view, setView] = useState<View>("active");
  const [range, setRange] = useState<EventRange>("upcoming");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [month, setMonth] = useState(() => new Date());
  const [localKey, setLocalKey] = useState(0);
  const [showEditor, setShowEditor] = useState(false);
  const [editing, setEditing] = useState<EventItem | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const dataRefresh = refreshKey + localKey;
  const status = view === "done" ? "done" : "planned";
  const day = view === "active" ? selectedDay : null;
  const { events, loading, error, create, update, complete, remove } = useEvents(
    view === "done" ? "all" : range,
    dataRefresh,
    { status, day },
  );
  const { events: monthEvents } = useMonthEvents(month, dataRefresh);

  const marks = useMemo(
    () => new Set(monthEvents.map((event) => eventDayKey(event))),
    [monthEvents],
  );

  const visibleEvents = useMemo(() => {
    if (view !== "done") {
      return events;
    }
    return [...events].sort((left, right) =>
      (right.completed_at ?? "").localeCompare(left.completed_at ?? ""),
    );
  }, [events, view]);

  function bump() {
    setLocalKey((value) => value + 1);
  }

  async function handleComplete(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      await complete(id);
      bump();
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
      bump();
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
    bump();
  }

  function switchView(next: View) {
    setView(next);
    if (next === "done") {
      setSelectedDay(null);
    }
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
            {loading ? "—" : String(visibleEvents.length).padStart(2, "0")}
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

      <div className="timeline-views">
        <div className="tabs" role="tablist" aria-label="Статус событий">
          <button
            type="button"
            role="tab"
            aria-selected={view === "active"}
            className={`tab ${view === "active" ? "tab--active" : ""}`}
            onClick={() => switchView("active")}
          >
            Активные
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "done"}
            className={`tab ${view === "done" ? "tab--active" : ""}`}
            onClick={() => switchView("done")}
          >
            Выполненные
          </button>
        </div>
        <span className="timeline-bar__hint">
          {view === "done"
            ? "выполненные не висят в общем списке"
            : "время — в вашем часовом поясе"}
        </span>
      </div>

      {(error || actionError) && <p className="form-error">{actionError ?? error}</p>}

      {view === "active" ? (
        <div className="timeline-layout">
          <EventCalendar
            month={month}
            marks={marks}
            selected={selectedDay}
            onSelect={setSelectedDay}
            onMonthChange={(next) => {
              setMonth(next);
              setSelectedDay(null);
            }}
          />

          <div className="timeline-main">
            <div className="timeline-bar">
              <div className="tabs" role="tablist" aria-label="Период">
                {RANGES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    role="tab"
                    aria-selected={range === item.value && !selectedDay}
                    className={`tab ${
                      range === item.value && !selectedDay ? "tab--active" : ""
                    }`}
                    onClick={() => {
                      setRange(item.value);
                      setSelectedDay(null);
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {selectedDay && (
              <div className="day-filter">
                <span>{formatDayLabel(selectedDay)}</span>
                <button
                  type="button"
                  className="button button--small button--ghost"
                  onClick={() => setSelectedDay(null)}
                >
                  Сбросить
                </button>
              </div>
            )}

            {loading && <p className="hint">Загрузка…</p>}
            {!loading && visibleEvents.length === 0 && (
              <div className="empty-state empty-state--compact">
                <p className="empty-state__index">00 / 00</p>
                <h2>{selectedDay ? "На этот день пусто." : "Пока пусто."}</h2>
                <p>
                  {selectedDay
                    ? "Выберите другой день или создайте событие."
                    : "Создайте первое событие или попросите ассистента сделать это за вас."}
                </p>
                {!selectedDay && (
                  <button
                    className="button button--ghost"
                    type="button"
                    onClick={openCreate}
                  >
                    Создать событие
                  </button>
                )}
              </div>
            )}

            <div className="event-list">
              {visibleEvents.map((event) => (
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
          </div>
        </div>
      ) : (
        <>
          {loading && <p className="hint">Загрузка…</p>}
          {!loading && visibleEvents.length === 0 && (
            <div className="empty-state">
              <p className="empty-state__index">00 / 00</p>
              <h2>Пока нет выполненных.</h2>
              <p>Отметьте событие выполненным — оно переедет сюда.</p>
            </div>
          )}
          <div className="event-list">
            {visibleEvents.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                busy={busyId === event.id}
                onDelete={(id) => void handleDelete(id)}
                onEdit={openEdit}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
