import { apiRequest } from "./client";
import type { ChatResponse, VoiceResponse } from "../types/api";

const TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";

export function sendChat(text: string, sessionId: string | null): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      text,
      session_id: sessionId,
      timezone: TIMEZONE,
    }),
  });
}

export function answerClarification(
  clarificationId: string,
  text: string,
  sessionId: string | null,
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>(`/clarifications/${clarificationId}/answer`, {
    method: "POST",
    body: JSON.stringify({
      text,
      session_id: sessionId,
    }),
  });
}

export function sendVoice(
  audio: Blob,
  sessionId: string | null,
): Promise<VoiceResponse> {
  const form = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : "webm";
  form.set("file", audio, `voice.${extension}`);
  form.set("timezone", TIMEZONE);
  if (sessionId) {
    form.set("session_id", sessionId);
  }

  return apiRequest<VoiceResponse>("/voice", {
    method: "POST",
    body: form,
  });
}
