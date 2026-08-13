// WebSocket message contract — mirrors docs/15-api-websocket-spec.md

export type SessionState = "idle" | "listening" | "processing" | "speaking" | "loading_model";

export type ServerMessage =
  | { type: "ready"; payload: { server_version: string; ollama_ok: boolean } }
  | {
      type: "state";
      // Счётчик вопросов приходит вместе с состоянием (doc 15). Поля
      // необязательные: у review-сессии и у терминальных состояний их нет.
      payload: {
        value: SessionState;
        question_index?: number | null;
        question_total?: number | null;
        question_kind?: string | null;
      };
    }
  | { type: "transcript"; payload: { role: "user" | "agent"; text: string; final: boolean } }
  | { type: "audio"; payload: { chunk_base64: string; mime: string; final: boolean } }
  | { type: "session_started"; payload: { session_kind: string; session_id: string } }
  | {
      type: "session_ended";
      payload: {
        session_kind: string;
        session_id: string;
        duration_sec: number;
        next_action: string;
      };
    }
  | { type: "error"; payload: { code: string; message: string; recoverable: boolean } }
  | { type: "pong"; payload: Record<string, never> };

const SERVER_TYPES = new Set([
  "ready",
  "state",
  "transcript",
  "audio",
  "session_started",
  "session_ended",
  "error",
  "pong",
]);

export function parseServerMessage(raw: string): ServerMessage | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const message = data as { type?: unknown; payload?: unknown };
  if (typeof message.type !== "string" || !SERVER_TYPES.has(message.type)) return null;
  if (typeof message.payload !== "object" || message.payload === null) return null;
  return message as ServerMessage;
}

export function clientMessage(
  type: "hello" | "start_interview" | "start_review" | "utterance_end" | "end_session" | "ping",
  payload: Record<string, unknown> = {},
): string {
  return JSON.stringify({ type, payload });
}
