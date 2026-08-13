import { turnTimestamp } from "../lib/format";
import type { TranscriptTurn } from "../types/api";

/** Сохранённый транскрипт — тот же диалог, что в живой сессии, плюс отметки времени. */
export function TranscriptView({ turns }: { turns: TranscriptTurn[] }) {
  if (!turns.length) return <p className="muted">Empty transcript.</p>;
  return (
    <div className="glass session">
      <div className="turns turns-full">
        {turns.map((turn) => (
          <div key={turn.turn_index} className={`bubble bubble-${turn.role}`}>
            <span className="bubble-who">
              {turn.role === "agent" ? "Henry" : "You"} · {turnTimestamp(turn.timestamp_ms)}
            </span>
            {turn.text}
          </div>
        ))}
      </div>
    </div>
  );
}
