import type { SessionState } from "../types/messages";

const LABELS: Record<SessionState, string> = {
  idle: "Idle",
  listening: "Listening…",
  processing: "Thinking…",
  speaking: "Speaking",
  loading_model: "Loading model…",
};

export function SessionStateRing({ state }: { state: SessionState }) {
  return (
    <div className={`state-ring state-${state}`} role="status">
      <span>{LABELS[state]}</span>
    </div>
  );
}
