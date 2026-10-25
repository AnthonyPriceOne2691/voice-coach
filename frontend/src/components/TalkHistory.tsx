import { useEffect, useState } from "react";

import { api } from "../lib/api";
import { formatSessionSpan } from "../lib/format";
import type { TalkDetail, TalkListItem } from "../types/api";

import { LanguageNotes } from "./LanguageNotes";
import { ListState } from "./ListState";
import { SessionWhen } from "./SessionWhen";
import { TranscriptView } from "./TranscriptView";

function notesLabel(count: number): string {
  if (count === 0) return "No language notes";
  return count === 1 ? "1 language note" : `${count} language notes`;
}

/** Разговоры в History (C13): у строки нет Review и Delete — только открыть. */
export function TalkList({ onOpen }: { onOpen: (talk: TalkDetail) => void }) {
  const [items, setItems] = useState<TalkListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTalks()
      .then(setItems)
      .catch(() => setError("Failed to load talks — is the backend running?"));
  }, []);

  const open = (id: string) => {
    api
      .getTalk(id)
      .then(onOpen)
      .catch(() => setError("Failed to open the talk — is the backend running?"));
  };

  return (
    <>
      <h2 className="section-title">Talks</h2>
      <ListState items={items} error={error} empty="No talks yet — start one on the Talk tab.">
        {(list) =>
          list.map((item) => (
            <div key={item.id} className="glass row">
              <SessionWhen item={item}>
                <span className="pill pill-quiet">{notesLabel(item.notes_count)}</span>
              </SessionWhen>
              <div className="row-actions">
                <button className="btn" onClick={() => open(item.id)}>
                  Open
                </button>
              </div>
            </div>
          ))
        }
      </ListState>
    </>
  );
}

/** Открытый разговор: заметки «было → лучше», потом сам разговор. */
export function TalkDetailPanel({ talk, onBack }: { talk: TalkDetail; onBack: () => void }) {
  return (
    <div>
      <button className="btn btn-quiet" onClick={onBack}>
        ← Back to history
      </button>
      <h2 className="section-title">
        Talk · {formatSessionSpan(talk.started_at, talk.ended_at, talk.duration_sec)}
      </h2>
      <LanguageNotes talkId={talk.id} notes={talk.language_notes} />
      <h2 className="section-title">Transcript</h2>
      <TranscriptView turns={talk.transcript} />
    </div>
  );
}
