import { SILENCE_THRESHOLD_DBFS } from "../lib/vad";

const FLOOR = -70; // dBFS shown as empty bar

function toPercent(dbfs: number): number {
  if (!isFinite(dbfs)) return 0;
  return Math.min(100, Math.max(0, ((dbfs - FLOOR) / -FLOOR) * 100));
}

/** Live mic level with the VAD threshold marker — shows whether the agent can hear you. */
export function MicLevelMeter({ level }: { level: number }) {
  const heard = level > SILENCE_THRESHOLD_DBFS;
  return (
    <div className="mic-meter" title={`mic: ${isFinite(level) ? level.toFixed(0) : "-∞"} dBFS`}>
      <span className="mic-meter-label">🎙</span>
      <div className="mic-meter-track">
        <div
          className={`mic-meter-fill ${heard ? "mic-heard" : ""}`}
          style={{ width: `${toPercent(level)}%` }}
        />
        <div
          className="mic-meter-threshold"
          style={{ left: `${toPercent(SILENCE_THRESHOLD_DBFS)}%` }}
        />
      </div>
      <span className={`mic-meter-status ${heard ? "mic-heard" : ""}`}>
        {heard ? "hearing you" : "silent"}
      </span>
    </div>
  );
}
