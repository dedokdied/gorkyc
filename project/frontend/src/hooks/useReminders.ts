import { useCallback, useEffect, useState } from "react";
import { acknowledgeReminder, fetchReminders } from "../api/reminders";
import type { EventItem } from "../types/api";

const POLL_MS = 30_000;

export function useReminders() {
  const [reminders, setReminders] = useState<EventItem[]>([]);

  const reload = useCallback(async () => {
    try {
      setReminders(await fetchReminders());
    } catch {
      // Reminders are best-effort: a failed poll must not break the workspace.
    }
  }, []);

  useEffect(() => {
    void reload();
    const timer = window.setInterval(() => void reload(), POLL_MS);
    const onFocus = () => void reload();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, [reload]);

  const dismiss = useCallback(async (id: string) => {
    setReminders((current) => current.filter((item) => item.id !== id));
    try {
      await acknowledgeReminder(id);
    } catch {
      // If ack failed the next poll brings the reminder back.
    }
  }, []);

  return { reminders, dismiss, reload };
}
