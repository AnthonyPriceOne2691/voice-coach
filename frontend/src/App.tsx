import { useState } from "react";

import { HistoryPage } from "./pages/HistoryPage";
import { InterviewPage } from "./pages/InterviewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { WordsPage } from "./pages/WordsPage";

type Tab = "interview" | "history" | "words" | "settings";

const TABS: [Tab, string][] = [
  ["interview", "Interview"],
  ["history", "History"],
  ["words", "Useful Words"],
  ["settings", "Settings"],
];

export default function App() {
  const [tab, setTab] = useState<Tab>("interview");
  const [reviewTarget, setReviewTarget] = useState<string | null>(null);

  const startReviewFor = (interviewId: string) => {
    setReviewTarget(interviewId);
    setTab("interview");
  };

  return (
    <main className="app">
      {/* Бренд — тихая строка, а не заголовок во всю ширину: пользователь знает,
          где он, и первый визуальный приоритет должен доставаться действию. */}
      <div className="topbar">
        <div className="brand">
          <span className="brand-dot" aria-hidden="true" />
          Voice Interview Coach
        </div>
        <nav className="tabs">
          {TABS.map(([name, label]) => (
            <button
              key={name}
              className={`tab ${tab === name ? "active" : ""}`}
              onClick={() => setTab(name)}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* key на обёртке перезапускает анимацию появления при смене вкладки */}
      <div className="page" key={tab}>
        {tab === "interview" && (
          <InterviewPage
            reviewTarget={reviewTarget}
            onReviewStarted={() => setReviewTarget(null)}
          />
        )}
        {tab === "history" && <HistoryPage onStartReview={startReviewFor} />}
        {tab === "words" && <WordsPage />}
        {tab === "settings" && <SettingsPage />}
      </div>
    </main>
  );
}
