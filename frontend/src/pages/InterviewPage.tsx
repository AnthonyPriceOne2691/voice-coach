import { useState } from "react";
import { MicLevelMeter } from "../components/MicLevelMeter";
import { SessionStateRing } from "../components/SessionStateRing";
import { TranscriptPanel } from "../components/TranscriptPanel";
import { useVoiceSession } from "../hooks/useVoiceSession";
import { api } from "../lib/api";

interface Props {
  reviewTarget: string | null;
  onReviewStarted: () => void;
}

export function InterviewPage({ reviewTarget, onReviewStarted }: Props) {
  const { state, transcript, error, active, micLevel, ended, start, end } = useVoiceSession();
  const [notice, setNotice] = useState<string | null>(null);

  const startReview = (interviewId: string) => {
    setNotice(null);
    onReviewStarted();
    void start({ interviewId });
  };

  const skipReview = async (interviewId: string) => {
    setNotice("Generating a minimal summary…");
    try {
      await api.minimalSummary(interviewId);
      setNotice("Minimal summary saved — see History. Full rubric unlocks after a review.");
    } catch {
      setNotice("Summary generation failed — you can retry from History.");
    }
  };

  return (
    <div>
      <p className="subtitle">Mock technical interview with Henry · ~15 min · English</p>

      <SessionStateRing state={state} />
      {active && state === "listening" && <MicLevelMeter level={micLevel} />}

      {error && <div className="error-banner">{error}</div>}
      {notice && <div className="notice-banner">{notice}</div>}

      {ended?.session_kind === "interview" && ended.next_action === "offer_review" && (
        <div className="modal-card">
          <h3>Interview complete 🎉</h3>
          <p>Review it together with your recruiter friend?</p>
          <div className="controls">
            <button className="btn btn-start" onClick={() => startReview(ended.session_id)}>
              Start Review Together
            </button>
            <button className="btn btn-ghost" onClick={() => void skipReview(ended.session_id)}>
              Skip for now
            </button>
          </div>
        </div>
      )}

      {ended?.session_kind === "review" && (
        <div className="notice-banner">
          Review saved. Henry is writing your full summary — it will appear in History shortly.
        </div>
      )}

      <div className="controls">
        {active ? (
          <button className="btn btn-end" onClick={end}>
            End session
          </button>
        ) : reviewTarget ? (
          <button className="btn btn-start" onClick={() => startReview(reviewTarget)}>
            Start Review Together
          </button>
        ) : (
          <button className="btn btn-start" onClick={() => void start()}>
            Start Mock Interview
          </button>
        )}
      </div>

      <TranscriptPanel entries={transcript} />
    </div>
  );
}
