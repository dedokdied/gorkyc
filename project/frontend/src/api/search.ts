import { apiRequest } from "./client";
import type { EventType, SearchResponse } from "../types/api";

export function searchEvents(
  query: string,
  type?: EventType,
  limit = 10,
): Promise<SearchResponse> {
  return apiRequest<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify({ query, type, limit }),
  });
}
