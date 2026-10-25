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

type Play = (url: string) => Promise<void>;

/**
 * Listen звучит, только пока заметки на экране (echo-защита).
 *
 * Звук идёт мимо очереди сессии (`AudioQueue`), и колбэк «отзвучало», по которому
 * открывается запись, о нём не знает. Заметки уходят с экрана, как только стартует
 * сессия (`start` сбрасывает `ended`) или меняется вкладка, — звук смолкает вместе с
 * ними, раньше, чем запись откроется после приветствия. Без уборки длинная фраза
 * могла бы доиграть в уже открытый микрофон.
 *
 * Набор один на всё время монтирования: уборка гасит каждый звук, начатый за это
 * время, а не только последний — две фразы подряд звучат вместе.
 */
function usePlayer(): Play {
  const [started] = useState(() => new Set<HTMLAudioElement>());
  useEffect(() => () => started.forEach((audio) => audio.pause()), [started]);
  return (url) => {
    const audio = new Audio(url);
    started.add(audio);
    return audio.play();
  };
}

/**
 * Одна заметка: что сказано — тихо, как лучше — ярко, и два действия.
 *
 * Состояние кнопок своё у каждой заметки: «добавлено» у одной не значит ничего
 * для соседней. Повтор после «добавлено» и «уже там» с экрана не уходит; сервер
 * всё равно не дублирует (C12), но лишний запрос к модели незачем.
 */
function NoteRow({
  talkId,
  index,
  note,
  play,
}: {
  talkId: string;
  index: number;
  note: LanguageNote;
  play: Play;
}) {
  const [add, setAdd] = useState<AddState>("idle");
  const [silent, setSilent] = useState(false);

  const listen = () => {
    setSilent(false);
    play(api.noteAudioUrl(talkId, index)).catch(() => setSilent(true));
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
  const play = usePlayer();
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
              <NoteRow key={index} talkId={talkId} index={index} note={note} play={play} />
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
