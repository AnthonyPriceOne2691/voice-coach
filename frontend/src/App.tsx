import { MicLevelMeter } from "./components/MicLevelMeter";
import { SessionStateRing } from "./components/SessionStateRing";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { useVoiceSession } from "./hooks/useVoiceSession";

export default function App() {
  const { state, transcript, error, active, micLevel, start, end } = useVoiceSession();

  return (
    <main className="app">
      <header>
        <h1>Voice Interview Coach</h1>
        <p className="subtitle">Mock technical interview · ~15 min · English</p>
      </header>

      <SessionStateRing state={state} />
      {active && <MicLevelMeter level={micLevel} />}

      {error && <div className="error-banner">{error}</div>}

      <div className="controls">
        {active ? (
          <button className="btn btn-end" onClick={end}>
            End session
          </button>
        ) : (
          <button className="btn btn-start" onClick={() => void start()}>
            Start Mock Interview
          </button>
        )}
      </div>

      <TranscriptPanel entries={transcript} />
    </main>
  );
}
