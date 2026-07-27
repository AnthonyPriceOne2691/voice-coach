import { useState } from "react";
import { HistoryPage } from "./pages/HistoryPage";
import { InterviewPage } from "./pages/InterviewPage";
import { WordsPage } from "./pages/WordsPage";

type Tab = "interview" | "history" | "words";

export default function App() {
  const [tab, setTab] = useState<Tab>("interview");
  const [reviewTarget, setReviewTarget] = useState<string | null>(null);

  const startReviewFor = (interviewId: string) => {
    setReviewTarget(interviewId);
    setTab("interview");
  };

  return (
    <main className="app">
      <header>
        <h1>Voice Interview Coach</h1>
        <nav className="tabs">
          {(
            [
              ["interview", "Interview"],
              ["history", "History"],
              ["words", "Useful Words"],
            ] as [Tab, string][]
          ).map(([name, label]) => (
            <button
              key={name}
              className={`tab ${tab === name ? "active" : ""}`}
              onClick={() => setTab(name)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      {tab === "interview" && (
        <InterviewPage reviewTarget={reviewTarget} onReviewStarted={() => setReviewTarget(null)} />
      )}
      {tab === "history" && <HistoryPage onStartReview={startReviewFor} />}
      {tab === "words" && <WordsPage />}
    </main>
  );
}
