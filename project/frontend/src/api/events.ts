import { apiRequest } from "./client";
import type { EventCreate, EventItem, EventType } from "../types/api";

export interface EventQuery {
  from?: string;
  to?: string;
  type?: EventType;
}

export function listEvents(query: EventQuery = {}): Promise<EventItem[]> {
  const params = new URLSearchParams();
  if (query.from) params.set("from", query.from);
  if (query.to) params.set("to", query.to);
  if (query.type) params.set("type", query.type);
  const suffix = params.toString();
  return apiRequest<EventItem[]>(`/events${suffix ? `?${suffix}` : ""}`);
}

export function createEvent(payload: EventCreate): Promise<EventItem> {
  return apiRequest<EventItem>("/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function completeEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/${id}/complete`, { method: "POST" });
}

export function deleteEvent(id: string): Promise<void> {
  return apiRequest<void>(`/events/${id}`, { method: "DELETE" });
}
