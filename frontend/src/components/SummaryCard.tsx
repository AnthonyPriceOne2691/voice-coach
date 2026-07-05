import type { Debrief } from "../types/api";

const SCORE_LABELS: Record<string, string> = {
  clarity: "Clarity",
  structure: "Structure",
  technical_depth: "Depth",
  english_fluency: "English",
  positioning: "Positioning",
};

export function SummaryCard({ debrief }: { debrief: Debrief }) {
  return (
    <div className="summary-card">
      {debrief.overall_summary && <p className="summary-overall">{debrief.overall_summary}</p>}

      {debrief.scores && (
        <section>
          <h3>Scores</h3>
          {Object.entries(SCORE_LABELS).map(([key, label]) => {
            const value = debrief.scores?.[key];
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
      )}

      {!!debrief.strengths?.length && (
        <section>
          <h3>Strengths</h3>
          <ul>
            {debrief.strengths.map((s, i) => (
              <li key={i}>
                {s.text} {s.reference && <em className="muted">({s.reference})</em>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!!debrief.improvements?.length && (
        <section>
          <h3>Improve</h3>
          <ul>
            {debrief.improvements.map((item, i) => (
              <li key={i}>
                <strong>{item.problem}</strong>
                {item.evidence && <span className="muted"> — {item.evidence}</span>}
                <div>Fix: {item.fix}</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!!debrief.weak_answers?.length && (
        <section>
          <h3>Weak answers — try instead</h3>
          <ul>
            {debrief.weak_answers.map((item, i) => (
              <li key={i}>
                <span className="muted">{item.question}</span>
                <div>“{item.suggested_rephrase}”</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!!debrief.vocabulary?.length && (
        <section>
          <h3>Words added ({debrief.vocabulary.length}) → see Useful Words tab</h3>
          <p className="muted">{debrief.vocabulary.map((v) => v.term_en).join(" · ")}</p>
        </section>
      )}

      {!!debrief.next_session_focus?.length && (
        <section>
          <h3>Next focus</h3>
          <p>{debrief.next_session_focus.join(" · ")}</p>
        </section>
      )}
    </div>
  );
}
