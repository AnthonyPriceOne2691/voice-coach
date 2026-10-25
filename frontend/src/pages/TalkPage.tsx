import { EndedTalkNotes } from "../components/LanguageNotes";
import { LiveSession, PastTranscript } from "../components/LiveSession";
import { StateOrb } from "../components/StateOrb";
import { useLiveTranscriptSetting } from "../hooks/useLiveTranscriptSetting";
import { useVoiceSession } from "../hooks/useVoiceSession";

/**
 * Разговор с Генри (D3a): беседа на повседневные темы для разговорного английского.
 * Голосовая оболочка та же, что у интервью; структуру разговора держит сервер —
 * тему, прощание и просьбы к Генри он узнаёт сам, экран их только показывает.
 */
export function TalkPage() {
  const session = useVoiceSession();
  const { transcript, error, active, ended } = session;
  const showLiveTranscript = useLiveTranscriptSetting();
  // Заметки «было → лучше» пишет сервер по ходу разговора; после конца — его список.
  const endedTalk = ended?.session_kind === "talk" ? ended.session_id : null;

  return (
    <div>
      {error && <div className="banner banner-error">{error}</div>}
      {ended?.session_kind === "talk" && (
        <div className="banner banner-ok">Nice talk — see you next time.</div>
      )}
      {active ? (
        <LiveSession
          session={session}
          showTranscript={showLiveTranscript}
          label="Talk with Henry"
        />
      ) : (
        <div className="glass hero">
          <div className="hero-text">
            <h1>Just talk.</h1>
            <p>
              A relaxed conversation with Henry about anything — your day, work, plans, trips.
              Practice your spoken English with a friend, not an examiner.
            </p>
            <div className="chips">
              <span className="chip">Everyday topics</span>
              <span className="chip">English only</span>
              <span className="chip">No grades</span>
            </div>
            <div className="cta">
              {/* `data-testid` — крючок для браузерного стенда, как у интервью (L66) */}
              <button
                className="btn"
                data-testid="start-talk"
                onClick={() => void session.start({ kind: "talk" })}
              >
                Start talking
              </button>
              <span className="faint">
                Say “let&apos;s talk about something else” or “bye” any time.
              </span>
            </div>
          </div>
          <StateOrb state="idle" />
        </div>
      )}
      {!active && endedTalk && <EndedTalkNotes talkId={endedTalk} />}
      {!active && <PastTranscript entries={transcript} />}
    </div>
  );
}
