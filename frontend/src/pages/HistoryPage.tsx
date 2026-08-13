import { useCallback, useEffect, useState } from "react";

import { ListState } from "../components/ListState";
import { SummaryCard } from "../components/SummaryCard";
import { TranscriptView } from "../components/TranscriptView";
import { api } from "../lib/api";
import { formatSessionSpan } from "../lib/format";
import type { InterviewDetail, InterviewListItem, ReviewDetail } from "../types/api";

interface Props {
  onStartReview: (interviewId: string) => void;
}

type DetailTab = "summary" | "interview" | "review";

// Страница разрезана на три функции по ФАЗАМ экрана (список · деталь · вкладка
// summary), а не по размеру: цикломатическая сложность одной функции была 14 при
// пороге 10. Вкладка summary — самая ветвистая часть (есть дебриф / генерится /
// нечего показать), поэтому она вынесена первой.

function SummaryTab({
  detail,
  busy,
  onStartReview,
  onRefreshDetail,
  onGenerateMinimal,
}: {
  detail: InterviewDetail;
  busy: boolean;
  onStartReview: (interviewId: string) => void;
  onRefreshDetail: () => void;
  onGenerateMinimal: () => void;
}) {
  if (detail.debrief) {
    return (
      <>
        {detail.summary_kind === "minimal" && (
          <div className="notice-banner">
            Minimal summary. Full rubric unlocks after Review Together.{" "}
            <button className="btn-link" onClick={() => onStartReview(detail.id)}>
              Start review
            </button>
          </div>
        )}
        <SummaryCard debrief={detail.debrief} />
      </>
    );
  }
  if (detail.has_review) {
    return (
      <div className="notice-banner">
        No summary yet. It may still be generating —{" "}
        <button className="btn-link" onClick={onRefreshDetail}>
          refresh
        </button>
        .
      </div>
    );
  }
  return (
    <div className="notice-banner">
      No summary yet.{" "}
      <button className="btn-link" onClick={() => onStartReview(detail.id)}>
        Review together
      </button>{" "}
      for the full rubric, or{" "}
      <button className="btn-link" disabled={busy} onClick={onGenerateMinimal}>
        {busy ? "generating…" : "generate a minimal summary"}
      </button>
      .
    </div>
  );
}

function DetailPanel({
  detail,
  review,
  error,
  busy,
  tab,
  onTab,
  onBack,
  onStartReview,
  onRefreshDetail,
  onGenerateMinimal,
}: {
  detail: InterviewDetail;
  review: ReviewDetail | null;
  error: string | null;
  busy: boolean;
  tab: DetailTab;
  onTab: (tab: DetailTab) => void;
  onBack: () => void;
  onStartReview: (interviewId: string) => void;
  onRefreshDetail: () => void;
  onGenerateMinimal: () => void;
}) {
  return (
    <div>
      <button className="btn btn-ghost" onClick={onBack}>
        ← Back to History
      </button>
      <h2>{formatSessionSpan(detail.started_at, detail.ended_at, detail.duration_sec)}</h2>
      {error && <div className="error-banner">{error}</div>}

      <nav className="subtabs">
        {(["summary", "interview", "review"] as DetailTab[]).map((name) => (
          <button
            key={name}
            className={`subtab ${tab === name ? "active" : ""}`}
            onClick={() => onTab(name)}
          >
            {name === "summary" ? "Summary" : name === "interview" ? "Interview" : "Review"}
          </button>
        ))}
      </nav>

      {tab === "summary" && (
        <SummaryTab
          detail={detail}
          busy={busy}
          onStartReview={onStartReview}
          onRefreshDetail={onRefreshDetail}
          onGenerateMinimal={onGenerateMinimal}
        />
      )}
      {tab === "interview" && <TranscriptView turns={detail.transcript} />}
      {tab === "review" &&
        (review ? (
          <TranscriptView turns={review.transcript} />
        ) : (
          <p className="muted">No review yet for this interview.</p>
        ))}
    </div>
  );
}

function HistoryRow({
  item,
  onOpen,
  onStartReview,
  onRemove,
}: {
  item: InterviewListItem;
  onOpen: () => void;
  onStartReview: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="history-item">
      <div>
        <strong>{formatSessionSpan(item.started_at, item.ended_at, item.duration_sec)}</strong> ·{" "}
        {item.status}
        <div className="muted">
          Interview ✓ · Review {item.has_review ? "✓" : "—"} · Summary {item.summary_kind ?? "—"}
        </div>
      </div>
      <div className="history-actions">
        <button className="btn btn-ghost" onClick={onOpen}>
          View
        </button>
        <button className="btn btn-ghost" onClick={onStartReview}>
          {item.has_review ? "Review again" : "Start review"}
        </button>
        <button className="btn btn-ghost btn-danger" onClick={onRemove}>
          Delete
        </button>
      </div>
    </div>
  );
}

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
    setReview(detail.review_session_id ? await api.getReview(detail.review_session_id) : null);
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
      <DetailPanel
        detail={selected}
        review={review}
        error={error}
        busy={busy}
        tab={tab}
        onTab={setTab}
        onBack={() => setSelected(null)}
        onStartReview={onStartReview}
        onRefreshDetail={() => void open(selected.id)}
        onGenerateMinimal={() => void generateMinimal(selected.id)}
      />
    );
  }

  return (
    <div>
      <h2>History</h2>
      <ListState
        items={items}
        error={error}
        empty="No sessions yet — run your first mock interview."
      >
        {(list) =>
          list.map((item) => (
            <HistoryRow
              key={item.id}
              item={item}
              onOpen={() => void open(item.id)}
              onStartReview={() => onStartReview(item.id)}
              onRemove={() => void remove(item.id)}
            />
          ))
        }
      </ListState>
    </div>
  );
}
