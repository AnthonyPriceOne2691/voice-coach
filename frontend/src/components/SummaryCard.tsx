import type { Debrief } from "../types/api";

const SCORE_LABELS: Record<string, string> = {
  clarity: "Clarity",
  structure: "Structure",
  technical_depth: "Depth",
  english_fluency: "English",
  positioning: "Positioning",
};

// Каждая секция сама решает, есть ли ей что показывать, и сама возвращает null.
// Раньше все семь условий стояли в одной функции, и её цикломатическая сложность
// была 13 при пороге 10 (гейт сложности, ts-половина). Условие, унесённое внутрь
// секции, стоит там же, где данные, которые оно проверяет.

function Overall({ debrief }: { debrief: Debrief }) {
  if (!debrief.overall_summary) return null;
  return <p className="summary-overall">{debrief.overall_summary}</p>;
}

function Scores({ debrief }: { debrief: Debrief }) {
  const scores = debrief.scores;
  if (!scores) return null;
  return (
    <section>
      <h3>Scores</h3>
      {Object.entries(SCORE_LABELS).map(([key, label]) => {
        const value = scores[key];
        if (value == null) return null;
        return (
          <div key={key} className="score-row">
            <span className="score-label">{label}</span>
            <div className="score-track">
              <div className="score-fill" style={{ width: `${(value / 5) * 100}%` }} />
            </div>
            <span className="score-value">{value}/5</span>
          </div>
        );
      })}
    </section>
  );
}

function Strengths({ debrief }: { debrief: Debrief }) {
  const items = debrief.strengths;
  if (!items?.length) return null;
  return (
    <section>
      <h3>Strengths</h3>
      <ul>
        {items.map((s, i) => (
          <li key={i}>
            {s.text} {s.reference && <em className="muted">({s.reference})</em>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Improvements({ debrief }: { debrief: Debrief }) {
  const items = debrief.improvements;
  if (!items?.length) return null;
  return (
    <section>
      <h3>Improve</h3>
      <ul>
        {items.map((item, i) => (
          <li key={i}>
            <strong>{item.problem}</strong>
            {item.evidence && <span className="muted"> — {item.evidence}</span>}
            <div>Fix: {item.fix}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function WeakAnswers({ debrief }: { debrief: Debrief }) {
  const items = debrief.weak_answers;
  if (!items?.length) return null;
  return (
    <section>
      <h3>Weak answers — try instead</h3>
      <ul>
        {items.map((item, i) => (
          <li key={i}>
            <span className="muted">{item.question}</span>
            <div>“{item.suggested_rephrase}”</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Vocabulary({ debrief }: { debrief: Debrief }) {
  const items = debrief.vocabulary;
  if (!items?.length) return null;
  return (
    <section>
      <h3>Words added ({items.length}) → see Useful Words tab</h3>
      <p className="muted">{items.map((v) => v.term_en).join(" · ")}</p>
    </section>
  );
}

function NextFocus({ debrief }: { debrief: Debrief }) {
  const items = debrief.next_session_focus;
  if (!items?.length) return null;
  return (
    <section>
      <h3>Next focus</h3>
      <p>{items.join(" · ")}</p>
    </section>
  );
}

export function SummaryCard({ debrief }: { debrief: Debrief }) {
  return (
    <div className="glass summary">
      <Overall debrief={debrief} />
      <Scores debrief={debrief} />
      <Strengths debrief={debrief} />
      <Improvements debrief={debrief} />
      <WeakAnswers debrief={debrief} />
      <Vocabulary debrief={debrief} />
      <NextFocus debrief={debrief} />
    </div>
  );
}
