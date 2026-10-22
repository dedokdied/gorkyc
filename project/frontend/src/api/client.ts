import type { ApiErrorPayload } from "../types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");
const DEMO_USER_KEY = "voice-assistant-demo-user";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function getDemoUser(): string {
  return localStorage.getItem(DEMO_USER_KEY) || import.meta.env.VITE_DEMO_USER || "demo";
}

export function setDemoUser(value: string): void {
  localStorage.setItem(DEMO_USER_KEY, value.trim() || "demo");
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Demo-User", getDemoUser());
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      // The server may return an empty body for infrastructure errors.
    }
    throw new ApiError(
      response.status,
      payload.error?.code ?? "http_error",
      payload.error?.message ?? `HTTP ${response.status}`,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
