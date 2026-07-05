import { turnTimestamp } from "../lib/format";
import type { TranscriptTurn } from "../types/api";

export function TranscriptView({ turns }: { turns: TranscriptTurn[] }) {
  if (!turns.length) return <p className="muted">Empty transcript.</p>;
  return (
    <div className="transcript">
      {turns.map((turn) => (
        <p key={turn.turn_index} className={`turn turn-${turn.role}`}>
          <span className="muted">[{turnTimestamp(turn.timestamp_ms)}]</span>{" "}
          <strong>{turn.role === "agent" ? "Henry" : "You"}:</strong> {turn.text}
        </p>
      ))}
    </div>
  );
}
