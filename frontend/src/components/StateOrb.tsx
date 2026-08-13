import type { SessionState } from "../types/messages";

const LABELS: Record<SessionState, string> = {
  idle: "Ready",
  listening: "Listening",
  processing: "Thinking",
  speaking: "Speaking",
  loading_model: "Loading",
};

/**
 * Индикатор состояния сессии.
 *
 * Состояния различаются ПОВЕДЕНИЕМ кольца, а не только подписью: дышит на
 * listening, вращается на speaking, мерцает на processing, замирает до старта.
 * Подпись читают глазами, движение — периферийным зрением, а во время разговора
 * пользователь смотрит не на экран.
 */
export function StateOrb({ state, size = "lg" }: { state: SessionState; size?: "lg" | "sm" }) {
  return (
    <div className={`orb orb-${size} orb-${state}`} role="status" aria-label={LABELS[state]}>
      <span className="orb-ring" aria-hidden="true" />
      <span className="orb-core">
        <span className="orb-label">{LABELS[state]}</span>
      </span>
    </div>
  );
}
