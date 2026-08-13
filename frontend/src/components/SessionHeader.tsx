import { useEffect, useState } from "react";

import type { SessionState } from "../types/messages";

import { StateOrb } from "./StateOrb";

const SAYING: Record<SessionState, string> = {
  idle: "Ready",
  listening: "Listening…",
  processing: "Thinking…",
  speaking: "Henry is speaking",
  loading_model: "Loading the model…",
};

export interface QuestionProgress {
  index: number;
  total: number;
  kind: string | null;
}

function elapsed(startedAt: number, now: number): string {
  const seconds = Math.max(0, Math.floor((now - startedAt) / 1000));
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

/**
 * Шапка живой сессии: состояние словами, где мы в интервью, сколько идёт.
 *
 * Таймер считается ЗДЕСЬ, а не приходит с бэкенда: серверу знать о нём нечего,
 * а тик раз в секунду ничего не стоит.
 */
export function SessionHeader({
  state,
  progress,
  startedAt,
  onEnd,
}: {
  state: SessionState;
  progress: QuestionProgress | null;
  startedAt: number;
  onEnd: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="session-head">
      <StateOrb state={state} size="sm" />
      <div className="session-meta">
        <strong>{SAYING[state]}</strong>
        {progress
          ? `Question ${progress.index} of ${progress.total}${progress.kind ? ` · ${progress.kind}` : ""}`
          : "Mock interview with Henry"}
      </div>
      <div className="session-right">
        <span className="timer">{elapsed(startedAt, now)}</span>
        <button className="btn btn-quiet" onClick={onEnd}>
          End session
        </button>
      </div>
    </div>
  );
}
