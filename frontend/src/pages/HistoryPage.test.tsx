// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HistoryPage } from "./HistoryPage";

const FINISHED = {
  id: "t1",
  started_at: "2026-10-23T18:00:00+00:00",
  ended_at: "2026-10-23T18:12:00+00:00",
  duration_sec: 720,
  status: "completed",
  notes_count: 2,
};
// Брошенный разговор: конца нет, длительность итогом не является (L16).
const LEFT = { ...FINISHED, id: "t2", ended_at: null, duration_sec: null, notes_count: 0 };
const DETAIL = {
  ...FINISHED,
  transcript: [
    { role: "agent", text: "How was your day?", timestamp_ms: 0, turn_index: 0 },
    { role: "user", text: "Yesterday I go to the office.", timestamp_ms: 4000, turn_index: 1 },
  ],
  language_notes: [
    {
      turn_index: 1,
      kind: "error",
      said: "I go to the office",
      better: "I went to the office",
      why: "past tense",
      spoken: false,
    },
  ],
};

// Брошенное интервью: голова строки та же, что у разговора (`SessionWhen`).
const INTERVIEW = {
  id: "i1",
  started_at: "2026-10-22T09:00:00+00:00",
  ended_at: null,
  interview_mode: "technical_and_behavioral",
  duration_sec: 300,
  status: "failed",
  has_review: false,
  review_session_id: null,
  has_debrief: false,
  summary_kind: null,
};

/** Бэкенд History: разговоров два, деталь — первого; интервью — по заказу теста. */
function stubBackend(interviews: unknown[] = []) {
  const asked: string[] = [];
  const bodies: Record<string, unknown> = {
    "/sessions/interviews": { items: interviews },
    "/sessions/talks": { items: [FINISHED, LEFT] },
    "/sessions/talks/t1": DETAIL,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      asked.push(url);
      return Promise.resolve({
        ok: url in bodies,
        status: url in bodies ? 200 : 404,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(bodies[url]),
      });
    }),
  );
  return asked;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("History — разговоры (C13)", () => {
  it("строка: дата, длительность, число заметок; брошенный — not finished", async () => {
    stubBackend();
    render(<HistoryPage onStartReview={vi.fn()} />);

    expect(await screen.findByText("2 language notes")).toBeTruthy(); // C13
    expect(screen.getByText("No language notes")).toBeTruthy(); // C13
    const spans = screen.getAllByText(/^Oct \d+/).map((node) => node.textContent);
    expect(spans.some((span) => span?.endsWith("· 12 min"))).toBe(true); // C13: длительность
    expect(spans.some((span) => span?.endsWith("· not finished"))).toBe(true); // C13 (L16)
  });

  it("открыв разговор, видишь его заметки и транскрипт, а назад — список", async () => {
    const asked = stubBackend();
    render(<HistoryPage onStartReview={vi.fn()} />);

    fireEvent.click((await screen.findAllByRole("button", { name: "Open" }))[0]);

    expect(await screen.findByText("Language notes")).toBeTruthy(); // C13
    expect(screen.getByRole("listitem").textContent).toContain("→ I went to the office"); // C13
    expect(screen.getByText("Yesterday I go to the office.")).toBeTruthy(); // C13: транскрипт
    expect(asked).toContain("/sessions/talks/t1");

    fireEvent.click(screen.getByRole("button", { name: "← Back to history" }));
    expect(await screen.findByText("2 language notes")).toBeTruthy();
  });

  it("две секции — Interviews, под ней Talks; голова строки интервью та же (C13)", async () => {
    stubBackend([INTERVIEW]);
    render(<HistoryPage onStartReview={vi.fn()} />);

    expect(await screen.findByText("Not reviewed")).toBeTruthy(); // C13: строка интервью
    expect(await screen.findByText("2 language notes")).toBeTruthy(); // C13
    const titles = screen.getAllByRole("heading").map((node) => node.textContent);
    expect(titles).toEqual(["Interviews", "Talks"]); // C13: решение human:anthony 2026-10-23
    expect(screen.getByText("Interrupted")).toBeTruthy(); // C13: голова — SessionWhen
    expect(screen.getAllByText(/· not finished$/)).toHaveLength(2); // C13: интервью и разговор
  });
});
