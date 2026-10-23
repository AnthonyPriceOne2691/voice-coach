import { useEffect, useState } from "react";

import { api } from "../lib/api";
import type { LanguageNote } from "../types/api";

import { ListState } from "./ListState";

type AddState = "idle" | "busy" | AddedStatus | "failed";
type AddedStatus = "added" | "exists";

const ADD_LABEL: Record<AddState, string> = {
  idle: "Add to Useful Words",
  busy: "Adding…",
  added: "Added to Useful Words",
  exists: "Already in Useful Words",
  failed: "Couldn't add — try again",
};

/**
 * Одна заметка: что сказано — тихо, как лучше — ярко, и два действия.
 *
 * Состояние кнопок своё у каждой заметки: «добавлено» у одной не значит ничего
 * для соседней. Повтор после «добавлено» и «уже там» с экрана не уходит; сервер
 * всё равно не дублирует (C12), но лишний запрос к модели незачем.
 */
function NoteRow({ talkId, index, note }: { talkId: string; index: number; note: LanguageNote }) {
  const [add, setAdd] = useState<AddState>("idle");
  const [silent, setSilent] = useState(false);

  const listen = () => {
    setSilent(false);
    new Audio(api.noteAudioUrl(talkId, index)).play().catch(() => setSilent(true));
  };
  const addToWords = () => {
    setAdd("busy");
    api
      .addNoteToWords(talkId, index)
      .then((result) => setAdd(result.status))
      .catch(() => setAdd("failed"));
  };

  return (
    <li className="note">
      <div className="note-said">You said: “{note.said}”</div>
      <div className="note-better">
        → {note.better}
        {note.why && <span className="note-why"> — {note.why}</span>}
      </div>
      <div className="note-actions">
        <button className="btn btn-quiet" onClick={listen}>
          Listen
        </button>
        <button
          className="btn btn-quiet"
          disabled={add !== "idle" && add !== "failed"}
          onClick={addToWords}
        >
          {ADD_LABEL[add]}
        </button>
        {silent && <span className="faint">Can&apos;t play right now</span>}
      </div>
    </li>
  );
}

/**
 * «Было → лучше» по разговору (D3a.2). Заметки решает проверка речи на сервере;
 * экран их только показывает — оценок здесь нет ни в каком виде (C10).
 */
export function LanguageNotes({
  talkId,
  notes,
  error,
}: {
  talkId: string;
  notes: LanguageNote[] | null;
  error?: string | null;
}) {
  return (
    <>
      <h2 className="section-title">Language notes</h2>
      <ListState
        items={notes}
        error={error}
        empty="No language notes for this talk. They appear when Henry hears a phrase you could say better."
      >
        {(list) => (
          <ul className="glass notes">
            {list.map((note, index) => (
              <NoteRow key={index} talkId={talkId} index={index} note={note} />
            ))}
          </ul>
        )}
      </ListState>
    </>
  );
}

/** Заметки только что закончившегося разговора: сервер знает их по `session_id`. */
export function EndedTalkNotes({ talkId }: { talkId: string }) {
  const [notes, setNotes] = useState<LanguageNote[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setNotes(null);
    setError(null);
    api
      .getTalk(talkId)
      .then((talk) => setNotes(talk.language_notes))
      .catch(() => setError("Failed to load language notes — is the backend running?"));
  }, [talkId]);

  return <LanguageNotes talkId={talkId} notes={notes} error={error} />;
}
