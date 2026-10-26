export type EventType = "task" | "meeting" | "reminder";
export type EventStatus = "planned" | "done" | "cancelled";
export type EventSource = "text" | "voice" | "import";

export interface EventItem {
  id: string;
  type: EventType;
  status: EventStatus;
  title: string;
  description: string | null;
  starts_at: string | null;
  ends_at: string | null;
  due_at: string | null;
  duration_minutes: number | null;
  timezone: string;
  source: EventSource;
  recurrence: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface EventCreate {
  type: EventType;
  title: string;
  description?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  due_at?: string | null;
  duration_minutes?: number | null;
  timezone: string;
  recurrence?: string | null;
}

export interface EventPatch {
  title?: string;
  description?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  due_at?: string | null;
  duration_minutes?: number | null;
  timezone?: string;
  recurrence?: string | null;
}

export interface ActionInfo {
  name: string;
  status: "done" | "needs_clarification" | "failed";
  entity_id: string | null;
}

export interface Clarification {
  id: string;
  question: string;
  options: string[];
  missing: string[];
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  action: ActionInfo | null;
  clarification: Clarification | null;
  audio_url: string | null;
}

export interface ChatHistoryMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface VoiceResponse extends ChatResponse {
  transcript: string;
}

export interface SearchHit {
  event: EventItem;
  score: number;
  snippet: string;
}

export interface SearchResponse {
  items: SearchHit[];
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}
