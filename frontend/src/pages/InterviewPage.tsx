import { useState } from "react";

import { MicLevelMeter } from "../components/MicLevelMeter";
import { SessionHeader } from "../components/SessionHeader";
import { StateOrb } from "../components/StateOrb";
import { TranscriptPanel } from "../components/TranscriptPanel";
import { useVoiceSession, type SessionEnded } from "../hooks/useVoiceSession";
import { api } from "../lib/api";

interface Props {
  reviewTarget: string | null;
  onReviewStarted: () => void;
}

// Две ветвистые части вынесены из страницы: что показать ПОСЛЕ конца сессии и
// как выглядит приглашение. Обе — про состояние, а не про вёрстку, и обе
// давали странице цикломатическую сложность выше порога.

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
      <div className="banner banner-ok">
        Review saved. Henry is writing your full summary — it will appear in History shortly.
      </div>
    );
  }
  if (ended.next_action !== "offer_review") return null;
  return (
    <div className="glass offer">
      <h3>Interview complete</h3>
      <p>Go through it together with your recruiter friend?</p>
      <div className="cta">
        <button className="btn" onClick={() => onStartReview(ended.session_id)}>
          Review together
        </button>
        <button className="btn btn-quiet" onClick={() => onSkipReview(ended.session_id)}>
          Skip for now
        </button>
      </div>
    </div>
  );
}

function Invitation({
  reviewTarget,
  onStart,
  onStartReview,
}: {
  reviewTarget: string | null;
  onStart: () => void;
  onStartReview: (interviewId: string) => void;
}) {
  const review = reviewTarget !== null;
  return (
    <div className="glass hero">
      <div className="hero-text">
        <h1>{review ? "Let's go through it." : "Ready when you are."}</h1>
        <p>
          {review
            ? "Henry will walk your answers question by question — what was strong, what to sharpen."
            : "Mock technical interview with Henry — he mixes project questions with behavioral ones."}
        </p>
        <div className="chips">
          <span className="chip">~15 min</span>
          <span className="chip">English only</span>
          <span className="chip">6 questions · 3 technical · 3 behavioral</span>
        </div>
        <div className="cta">
          {review ? (
            <button className="btn" onClick={() => onStartReview(reviewTarget)}>
              Review together
            </button>
          ) : (
            <button className="btn" onClick={onStart}>
              Start interview
            </button>
          )}
          <span className="faint">Say “speak slower” any time — Henry will.</span>
        </div>
      </div>
      <StateOrb state="idle" />
    </div>
  );
}

export function InterviewPage({ reviewTarget, onReviewStarted }: Props) {
  const session = useVoiceSession();
  const { state, transcript, error, active, micLevel, ended, progress, startedAt } = session;
  const [notice, setNotice] = useState<string | null>(null);

  const startReview = (interviewId: string) => {
    setNotice(null);
    onReviewStarted();
    void session.start({ interviewId });
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
      {error && <div className="banner banner-error">{error}</div>}
      {notice && <div className="banner banner-ok">{notice}</div>}

      {/* До старта транскрипта на экране НЕТ: пустой прямоугольник в полэкрана
          ничего не сообщал и держал место, которое нужно приглашению. */}
      {active ? (
        <div className="glass session">
          <SessionHeader
            state={state}
            progress={progress}
            startedAt={startedAt}
            onEnd={session.end}
          />
          {state === "listening" && <MicLevelMeter level={micLevel} />}
          <TranscriptPanel entries={transcript} />
        </div>
      ) : (
        <Invitation
          reviewTarget={reviewTarget}
          onStart={() => void session.start()}
          onStartReview={startReview}
        />
      )}

      {ended && (
        <EndedCard
          ended={ended}
          onStartReview={startReview}
          onSkipReview={(id) => void skipReview(id)}
        />
      )}

      {/* Транскрипт последней сессии остаётся читаемым после её конца */}
      {!active && transcript.length > 0 && (
        <>
          <h2 className="section-title">Transcript</h2>
          <div className="glass session">
            <TranscriptPanel entries={transcript} />
          </div>
        </>
      )}
    </div>
  );
}
