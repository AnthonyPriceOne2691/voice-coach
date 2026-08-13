import { useEffect, useRef } from "react";

import type { TranscriptEntry } from "../hooks/useVoiceSession";

/**
 * Транскрипт как ДИАЛОГ, а не список строк.
 *
 * Реплики различаются стороной и формой пузыря, а не только цветом слова перед
 * двоеточием: разговор глаз читает по расположению, и «кто говорит» должно быть
 * понятно без чтения.
 */
export function TranscriptPanel({ entries }: { entries: TranscriptEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  return (
    <div className="turns">
      {entries.map((entry, index) => (
        <div key={index} className={`bubble bubble-${entry.role}`}>
          <span className="bubble-who">{entry.role === "agent" ? "Henry" : "You"}</span>
          {entry.text}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
