import { useCallback, useEffect, useState } from "react";
import {
  completeEvent,
  createEvent,
  deleteEvent,
  listEvents,
  type EventQuery,
} from "../api/events";
import type { EventCreate, EventItem } from "../types/api";

export type EventRange = "today" | "week" | "upcoming" | "all";

function rangeQuery(range: EventRange): EventQuery {
  if (range === "all") {
    return {};
  }

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (range === "today") {
    return {
      from: startOfToday.toISOString(),
      to: new Date(startOfToday.getTime() + 86_400_000).toISOString(),
    };
  }
  if (range === "week") {
    return {
      from: startOfToday.toISOString(),
      to: new Date(startOfToday.getTime() + 7 * 86_400_000).toISOString(),
    };
  }
  return {
    from: now.toISOString(),
    to: new Date(now.getTime() + 30 * 86_400_000).toISOString(),
  };
}

export function useEvents(range: EventRange, refreshKey: number) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await listEvents(rangeQuery(range)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить события");
    } finally {
      setLoading(false);
    }
  }, [range, refreshKey]);

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

  return { events, loading, error, reload, create, complete, remove };
}
