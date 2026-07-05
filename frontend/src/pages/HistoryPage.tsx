import { useCallback, useEffect, useState } from "react";
import { SummaryCard } from "../components/SummaryCard";
import { TranscriptView } from "../components/TranscriptView";
import { api } from "../lib/api";
import { formatDate, formatDuration } from "../lib/format";
import type { InterviewDetail, InterviewListItem, ReviewDetail } from "../types/api";

interface Props {
  onStartReview: (interviewId: string) => void;
}

type DetailTab = "summary" | "interview" | "review";

export function HistoryPage({ onStartReview }: Props) {
  const [items, setItems] = useState<InterviewListItem[] | null>(null);
  const [selected, setSelected] = useState<InterviewDetail | null>(null);
  const [review, setReview] = useState<ReviewDetail | null>(null);
  const [tab, setTab] = useState<DetailTab>("summary");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api
      .listInterviews()
      .then(setItems)
      .catch(() => setError("Failed to load history — is the backend running?"));
  }, []);

  useEffect(refresh, [refresh]);

  const open = async (id: string) => {
    setError(null);
    const detail = await api.getInterview(id);
    setSelected(detail);
    setTab(detail.debrief ? "summary" : "interview");
    setReview(
      detail.review_session_id ? await api.getReview(detail.review_session_id) : null,
    );
  };

  const remove = async (id: string) => {
    if (!window.confirm("Delete this interview and its review?")) return;
    await api.deleteInterview(id);
    setSelected(null);
    refresh();
  };

  const generateMinimal = async (id: string) => {
    setBusy(true);
    try {
      await api.minimalSummary(id);
      await open(id);
      refresh();
    } catch {
      setError("Summary generation failed — check that Ollama is running.");
    } finally {
      setBusy(false);
    }
  };

  if (selected) {
    return (
      <div>
        <button className="btn btn-ghost" onClick={() => setSelected(null)}>
          ← Back to History
        </button>
        <h2>
          {formatDate(selected.started_at)} · {formatDuration(selected.duration_sec)}
        </h2>
        {error && <div className="error-banner">{error}</div>}

        <nav className="subtabs">
          {(["summary", "interview", "review"] as DetailTab[]).map((name) => (
            <button
              key={name}
              className={`subtab ${tab === name ? "active" : ""}`}
              onClick={() => setTab(name)}
            >
              {name === "summary" ? "Summary" : name === "interview" ? "Interview" : "Review"}
            </button>
          ))}
        </nav>

        {tab === "summary" &&
          (selected.debrief ? (
            <>
              {selected.summary_kind === "minimal" && (
                <div className="notice-banner">
                  Minimal summary. Full rubric unlocks after Review Together.{" "}
                  <button className="btn-link" onClick={() => onStartReview(selected.id)}>
                    Start review
                  </button>
                </div>
              )}
              <SummaryCard debrief={selected.debrief} />
            </>
          ) : (
            <div className="notice-banner">
              No summary yet.{" "}
              {selected.has_review ? (
                <>It may still be generating — <button className="btn-link" onClick={() => void open(selected.id)}>refresh</button>.</>
              ) : (
                <>
                  <button className="btn-link" onClick={() => onStartReview(selected.id)}>
                    Review together
                  </button>{" "}
                  for the full rubric, or{" "}
                  <button
                    className="btn-link"
                    disabled={busy}
                    onClick={() => void generateMinimal(selected.id)}
                  >
                    {busy ? "generating…" : "generate a minimal summary"}
                  </button>
                  .
                </>
              )}
            </div>
          ))}
        {tab === "interview" && <TranscriptView turns={selected.transcript} />}
        {tab === "review" &&
          (review ? (
            <TranscriptView turns={review.transcript} />
          ) : (
            <p className="muted">No review yet for this interview.</p>
          ))}
      </div>
    );
  }

  return (
    <div>
      <h2>History</h2>
      {error && <div className="error-banner">{error}</div>}
      {items === null ? (
        <p className="muted">Loading…</p>
      ) : items.length === 0 ? (
        <p className="muted">No sessions yet — run your first mock interview.</p>
      ) : (
        items.map((item) => (
          <div key={item.id} className="history-item">
            <div>
              <strong>{formatDate(item.started_at)}</strong> ·{" "}
              {formatDuration(item.duration_sec)} · {item.status}
              <div className="muted">
                Interview ✓ · Review {item.has_review ? "✓" : "—"} · Summary{" "}
                {item.summary_kind ?? "—"}
              </div>
            </div>
            <div className="history-actions">
              <button className="btn btn-ghost" onClick={() => void open(item.id)}>
                View
              </button>
              <button className="btn btn-ghost" onClick={() => onStartReview(item.id)}>
                {item.has_review ? "Review again" : "Start review"}
              </button>
              <button className="btn btn-ghost btn-danger" onClick={() => void remove(item.id)}>
                Delete
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
