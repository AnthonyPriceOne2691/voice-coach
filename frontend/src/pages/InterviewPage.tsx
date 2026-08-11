import { useState } from "react";
import { MicLevelMeter } from "../components/MicLevelMeter";
import { SessionStateRing } from "../components/SessionStateRing";
import { TranscriptPanel } from "../components/TranscriptPanel";
import { useVoiceSession, type SessionEnded } from "../hooks/useVoiceSession";
import { api } from "../lib/api";

interface Props {
  reviewTarget: string | null;
  onReviewStarted: () => void;
}

// Две ветвистые части вынесены из страницы: что показать ПОСЛЕ конца сессии и
// какая кнопка стоит в контролах. Обе — про состояние, а не про верстку, и обе
// давали странице цикломатическую сложность 12 при пороге 10.

function EndedCard({
  ended,
  onStartReview,
  onSkipReview,
}: {
  ended: SessionEnded;
  onStartReview: (interviewId: string) => void;
  onSkipReview: (interviewId: string) => void;
}) {
  if (ended.session_kind === "review") {
    return (
      <div className="notice-banner">
        Review saved. Henry is writing your full summary — it will appear in History shortly.
      </div>
    );
  }
  if (ended.next_action !== "offer_review") return null;
  return (
    <div className="modal-card">
      <h3>Interview complete 🎉</h3>
      <p>Review it together with your recruiter friend?</p>
      <div className="controls">
        <button className="btn btn-start" onClick={() => onStartReview(ended.session_id)}>
          Start Review Together
        </button>
        <button className="btn btn-ghost" onClick={() => onSkipReview(ended.session_id)}>
          Skip for now
        </button>
      </div>
    </div>
  );
}

function SessionControls({
  active,
  reviewTarget,
  onEnd,
  onStartReview,
  onStartInterview,
}: {
  active: boolean;
  reviewTarget: string | null;
  onEnd: () => void;
  onStartReview: (interviewId: string) => void;
  onStartInterview: () => void;
}) {
  if (active) {
    return (
      <button className="btn btn-end" onClick={onEnd}>
        End session
      </button>
    );
  }
  if (reviewTarget) {
    return (
      <button className="btn btn-start" onClick={() => onStartReview(reviewTarget)}>
        Start Review Together
      </button>
    );
  }
  return (
    <button className="btn btn-start" onClick={onStartInterview}>
      Start Mock Interview
    </button>
  );
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

      {ended && (
        <EndedCard
          ended={ended}
          onStartReview={startReview}
          onSkipReview={(id) => void skipReview(id)}
        />
      )}

      <div className="controls">
        <SessionControls
          active={active}
          reviewTarget={reviewTarget}
          onEnd={end}
          onStartReview={startReview}
          onStartInterview={() => void start()}
        />
      </div>

      <TranscriptPanel entries={transcript} />
    </div>
  );
}
