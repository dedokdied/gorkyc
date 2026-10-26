import { apiRequest } from "./client";
import type {
  ChatHistoryMessage,
  ChatResponse,
  VoiceResponse,
} from "../types/api";

const TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";

function zone(value?: string): string {
  return value || TIMEZONE;
}

export function fetchHistory(
  sessionId: string | null,
): Promise<ChatHistoryMessage[]> {
  if (!sessionId) {
    return Promise.resolve([]);
  }
  return apiRequest<ChatHistoryMessage[]>(
    `/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  );
}

export function clearHistory(sessionId: string | null): Promise<void> {
  if (!sessionId) {
    return Promise.resolve();
  }
  return apiRequest<void>(
    `/chat/history?session_id=${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

export function sendChat(
  text: string,
  sessionId: string | null,
  timezone?: string,
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      text,
      session_id: sessionId,
      timezone: zone(timezone),
    }),
  });
}

export function answerClarification(
  clarificationId: string,
  text: string,
  sessionId: string | null,
  timezone?: string,
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>(`/clarifications/${clarificationId}/answer`, {
    method: "POST",
    body: JSON.stringify({
      text,
      session_id: sessionId,
      timezone: zone(timezone),
    }),
  });
}

export function sendVoice(
  audio: Blob,
  sessionId: string | null,
  timezone?: string,
): Promise<VoiceResponse> {
  const form = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : "webm";
  form.set("file", audio, `voice.${extension}`);
  form.set("timezone", zone(timezone));
  if (sessionId) {
    form.set("session_id", sessionId);
  }

  return apiRequest<VoiceResponse>("/voice", {
    method: "POST",
    body: form,
  });
}
