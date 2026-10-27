export type AssistantMode = "text" | "voice";

const MODE_KEY = "gorky-assistant-mode";

export function getStoredMode(): AssistantMode | null {
  const value = localStorage.getItem(MODE_KEY);
  return value === "text" || value === "voice" ? value : null;
}

export function setStoredMode(mode: AssistantMode): void {
  localStorage.setItem(MODE_KEY, mode);
}
