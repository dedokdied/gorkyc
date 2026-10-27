import { useCallback, useEffect, useState } from "react";
import {
  completeEvent,
  createEvent,
  deleteEvent,
  listEvents,
  updateEvent,
  type EventQuery,
} from "../api/events";
import type {
  EventCreate,
  EventItem,
  EventPatch,
  EventStatus,
} from "../types/api";

export type EventRange = "today" | "week" | "upcoming" | "all";

export interface EventFilter {
  status?: EventStatus;
  day?: string | null;
}

function dayQuery(day: string): EventQuery {
  const start = new Date(`${day}T00:00:00`);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return { from: start.toISOString(), to: end.toISOString() };
}

function rangeQuery(
  range: EventRange,
  status: EventStatus | undefined,
  day: string | null | undefined,
): EventQuery {
  if (day) {
    return { ...dayQuery(day), status };
  }
  if (range === "all") {
    return { status };
  }

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (range === "today") {
    return {
      from: startOfToday.toISOString(),
      to: new Date(startOfToday.getTime() + 86_400_000).toISOString(),
      status,
    };
  }
  if (range === "week") {
    return {
      from: startOfToday.toISOString(),
      to: new Date(startOfToday.getTime() + 7 * 86_400_000).toISOString(),
      status,
    };
  }
  return {
    from: now.toISOString(),
    to: new Date(now.getTime() + 30 * 86_400_000).toISOString(),
    status,
  };
}

export function useEvents(
  range: EventRange,
  refreshKey: number,
  filter: EventFilter = {},
) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const status = filter.status;
  const day = filter.day;

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await listEvents(rangeQuery(range, status, day)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить события");
    } finally {
      setLoading(false);
    }
  }, [range, refreshKey, status, day]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const create = useCallback(
    async (payload: EventCreate) => {
      const event = await createEvent(payload);
      await reload();
      return event;
    },
    [reload],
  );

  const complete = useCallback(
    async (id: string) => {
      await completeEvent(id);
      await reload();
    },
    [reload],
  );

  const remove = useCallback(
    async (id: string) => {
      await deleteEvent(id);
      await reload();
    },
    [reload],
  );

  const update = useCallback(
    async (id: string, payload: EventPatch) => {
      const event = await updateEvent(id, payload);
      await reload();
      return event;
    },
    [reload],
  );

  return { events, loading, error, reload, create, update, complete, remove };
}

export function useMonthEvents(month: Date, refreshKey: number) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const monthKey = `${month.getFullYear()}-${month.getMonth()}`;

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    const year = month.getFullYear();
    const monthIndex = month.getMonth();
    try {
      setEvents(
        await listEvents({
          from: new Date(year, monthIndex, 1).toISOString(),
          to: new Date(year, monthIndex + 1, 1).toISOString(),
          status: "planned",
        }),
      );
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Не удалось загрузить календарь",
      );
    } finally {
      setLoading(false);
    }
  }, [monthKey, refreshKey]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { events, loading, error };
}
