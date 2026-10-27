export type TelegramPromptDecision = "later" | "never";

const KEY_PREFIX = "zapishii-telegram-prompt:";

function key(userId: string): string {
  return `${KEY_PREFIX}${userId}`;
}

export function getTelegramPromptDecision(
  userId: string,
): TelegramPromptDecision | null {
  const value = localStorage.getItem(key(userId));
  return value === "later" || value === "never" ? value : null;
}

export function setTelegramPromptDecision(
  userId: string,
  decision: TelegramPromptDecision,
): void {
  localStorage.setItem(key(userId), decision);
}
