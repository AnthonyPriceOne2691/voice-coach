import { useEffect, useRef } from "react";
import type { TranscriptEntry } from "../hooks/useVoiceSession";

export function TranscriptPanel({ entries }: { entries: TranscriptEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  return (
    <div className="transcript">
      {entries.map((entry, index) => (
        <p key={index} className={`turn turn-${entry.role}`}>
          <strong>{entry.role === "agent" ? "Interviewer" : "You"}:</strong> {entry.text}
        </p>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
