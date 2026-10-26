import { apiRequest } from "./client";
import type { EventItem } from "../types/api";

export function fetchReminders(): Promise<EventItem[]> {
  return apiRequest<EventItem[]>("/reminders/inbox");
}

export function acknowledgeReminder(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/reminders/${id}/ack`, { method: "POST" });
}
