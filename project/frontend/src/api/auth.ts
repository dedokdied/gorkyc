import { apiRequest } from "./client";
import type { AuthResponse, AuthUser, RegisterPayload } from "../types/auth";

const TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";

export function register(payload: RegisterPayload): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      timezone: payload.timezone ?? TIMEZONE,
    }),
  });
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function me(): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me");
}

export function linkTelegram(code: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/link-telegram", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function updateProfile(payload: {
  display_name?: string;
  timezone?: string;
}): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
