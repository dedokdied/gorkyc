import { useCallback, useEffect, useRef, useState } from "react";
import {
  answerClarification,
  clearHistory,
  fetchHistory,
  sendChat,
  sendVoice,
} from "../api/chat";
import { clearSessionId, getSessionId, setSessionId } from "../store/session";
import type {
  ActionInfo,
  ChatResponse,
  Clarification,
} from "../types/api";

export interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  action?: ActionInfo | null;
  voice?: boolean;
}

function newId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

export function useChat(onEventChanged?: () => void, timezone?: string) {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [sessionId, setCurrentSessionId] = useState<string | null>(getSessionId);
  const [clarification, setClarification] = useState<Clarification | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialSessionRef = useRef(sessionId);

  useEffect(() => {
    let active = true;
    void fetchHistory(initialSessionRef.current)
      .then((rows) => {
        if (!active || rows.length === 0) {
          return;
        }
        setMessages((current) =>
          current.length > 0
            ? current
            : rows.map((row) => ({
                id: row.id,
                role: row.role,
                text: row.content,
              })),
        );
      })
      .catch(() => {
        // History is a convenience: the dialogue still works without it.
      });
    return () => {
      active = false;
    };
  }, []);

  const append = useCallback((entry: ChatEntry) => {
    setMessages((current) => [...current, entry]);
  }, []);

  const applyResponse = useCallback(
    (response: ChatResponse) => {
      setCurrentSessionId(response.session_id);
      setSessionId(response.session_id);
      setClarification(response.clarification);
      append({
        id: newId(),
        role: "assistant",
        text: response.reply,
        action: response.action,
      });
      if (response.action?.status === "done") {
        onEventChanged?.();
      }
    },
    [append, onEventChanged],
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) {
        return;
      }

      append({ id: newId(), role: "user", text: trimmed });
      setLoading(true);
      setError(null);
      try {
        applyResponse(await sendChat(trimmed, sessionId, timezone));
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "Ошибка запроса";
        setError(message);
        append({ id: newId(), role: "assistant", text: `Ошибка: ${message}` });
      } finally {
        setLoading(false);
      }
    },
    [applyResponse, append, loading, sessionId, timezone],
  );

  const answer = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !clarification || loading) {
        return;
      }

      append({ id: newId(), role: "user", text: trimmed });
      setLoading(true);
      setError(null);
      try {
        const response = await answerClarification(
          clarification.id,
          trimmed,
          sessionId,
          timezone,
        );
        setClarification(null);
        applyResponse(response);
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "Ошибка запроса";
        setError(message);
        append({ id: newId(), role: "assistant", text: `Ошибка: ${message}` });
      } finally {
        setLoading(false);
      }
    },
    [applyResponse, append, clarification, loading, sessionId, timezone],
  );

  const sendAudio = useCallback(
    async (audio: Blob) => {
      if (loading) {
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await sendVoice(audio, sessionId, timezone);
        append({
          id: newId(),
          role: "user",
          text: response.transcript,
          voice: true,
        });
        applyResponse(response);
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "Ошибка запроса";
        setError(message);
        append({ id: newId(), role: "assistant", text: `Ошибка: ${message}` });
      } finally {
        setLoading(false);
      }
    },
    [applyResponse, append, loading, sessionId, timezone],
  );

  const clear = useCallback(async () => {
    if (loading) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await clearHistory(sessionId);
      setMessages([]);
      setClarification(null);
      clearSessionId();
      setCurrentSessionId(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось очистить чат");
    } finally {
      setLoading(false);
    }
  }, [loading, sessionId]);

  return {
    messages,
    clarification,
    loading,
    error,
    send,
    answer,
    sendAudio,
    clear,
  };
}
