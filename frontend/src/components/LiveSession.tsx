import type { TranscriptEntry, VoiceSession } from "../hooks/useVoiceSession";

import { MicLevelMeter } from "./MicLevelMeter";
import { SessionHeader } from "./SessionHeader";
import { TranscriptPanel } from "./TranscriptPanel";

/**
 * Живая сессия: шапка, полоска уровня, транскрипт по переключателю Live transcript.
 * Общая для интервью и разговора — вторая копия разметки разъехалась бы с первой.
 */
export function LiveSession({
  session,
  showTranscript,
  label,
}: {
  session: VoiceSession;
  showTranscript: boolean;
  label?: string;
}) {
  const { state, progress, startedAt, micLevel, transcript } = session;
  return (
    <div className="glass session">
      <SessionHeader
        state={state}
        progress={progress}
        startedAt={startedAt}
        onEnd={session.end}
        label={label}
      />
      {state === "listening" && <MicLevelMeter level={micLevel} />}
      {showTranscript && <TranscriptPanel entries={transcript} />}
    </div>
  );
}

/** Транскрипт последней сессии остаётся читаемым после её конца. */
export function PastTranscript({ entries }: { entries: TranscriptEntry[] }) {
  if (entries.length === 0) return null;
  return (
    <>
      <h2 className="section-title">Transcript</h2>
      <div className="glass session">
        <TranscriptPanel entries={entries} />
      </div>
    </>
  );
}
