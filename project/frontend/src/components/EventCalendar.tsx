import { useMemo } from "react";

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export function dayKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function eventDayKey(event: {
  starts_at: string | null;
  due_at: string | null;
  created_at: string;
}): string {
  const value = event.starts_at ?? event.due_at ?? event.created_at;
  return dayKey(new Date(value));
}

export function formatDayLabel(day: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(`${day}T12:00:00`));
}

interface Props {
  month: Date;
  marks: Set<string>;
  selected: string | null;
  onSelect: (day: string | null) => void;
  onMonthChange: (month: Date) => void;
}

export function EventCalendar({
  month,
  marks,
  selected,
  onSelect,
  onMonthChange,
}: Props) {
  const year = month.getFullYear();
  const monthIndex = month.getMonth();
  const today = dayKey(new Date());

  const cells = useMemo(() => {
    const firstWeekday = (new Date(year, monthIndex, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
    const result: Array<number | null> = Array.from(
      { length: firstWeekday },
      () => null,
    );
    for (let day = 1; day <= daysInMonth; day += 1) {
      result.push(day);
    }
    while (result.length % 7 !== 0) {
      result.push(null);
    }
    return result;
  }, [year, monthIndex]);

  const title = new Intl.DateTimeFormat("ru-RU", {
    month: "long",
    year: "numeric",
  }).format(month);

  function shiftMonth(delta: number) {
    onMonthChange(new Date(year, monthIndex + delta, 1));
  }

  return (
    <section className="calendar" aria-label="Календарь событий">
      <header className="calendar__head">
        <button
          type="button"
          className="calendar__nav"
          aria-label="Предыдущий месяц"
          onClick={() => shiftMonth(-1)}
        >
          ←
        </button>
        <p className="calendar__title">{title}</p>
        <button
          type="button"
          className="calendar__nav"
          aria-label="Следующий месяц"
          onClick={() => shiftMonth(1)}
        >
          →
        </button>
      </header>

      <div className="calendar__weekdays" aria-hidden="true">
        {WEEKDAYS.map((weekday) => (
          <span key={weekday}>{weekday}</span>
        ))}
      </div>

      <div className="calendar__grid">
        {cells.map((day, index) => {
          if (day === null) {
            return <span key={`blank-${index}`} className="calendar__blank" />;
          }
          const key = dayKey(new Date(year, monthIndex, day));
          const marked = marks.has(key);
          const isSelected = selected === key;
          const isToday = today === key;
          return (
            <button
              key={key}
              type="button"
              aria-pressed={isSelected}
              aria-label={`${day}, ${marked ? "есть события" : "нет событий"}`}
              className={[
                "calendar__day",
                marked ? "calendar__day--marked" : "",
                isSelected ? "calendar__day--selected" : "",
                isToday ? "calendar__day--today" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => onSelect(isSelected ? null : key)}
            >
              <span>{day}</span>
              {marked && <span className="calendar__dot" aria-hidden="true" />}
            </button>
          );
        })}
      </div>

      <footer className="calendar__foot">
        <span className="calendar__legend">
          <span className="calendar__dot" aria-hidden="true" /> есть записи
        </span>
        {selected && (
          <button
            type="button"
            className="calendar__reset"
            onClick={() => onSelect(null)}
          >
            Сбросить день
          </button>
        )}
      </footer>
    </section>
  );
}
