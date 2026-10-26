import type { ApiErrorPayload } from "../types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");
const TOKEN_KEY = "gorky-auth-token";

export const UNAUTHORIZED_EVENT = "gorky:unauthorized";

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

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(value: string): void {
  localStorage.setItem(TOKEN_KEY, value);
}

export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function notifyUnauthorized(): void {
  clearAuthToken();
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
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

    if (response.status === 401 && token) {
      notifyUnauthorized();
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
