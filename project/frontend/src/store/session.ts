const SESSION_KEY = "voice-assistant-session-id";

export function getSessionId(): string | null {
  return localStorage.getItem(SESSION_KEY);
}

export function setSessionId(value: string): void {
  localStorage.setItem(SESSION_KEY, value);
}

export function clearSessionId(): void {
  localStorage.removeItem(SESSION_KEY);
}
