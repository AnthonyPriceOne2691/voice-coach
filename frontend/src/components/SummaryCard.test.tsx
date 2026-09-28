// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { Debrief } from "../types/api";

import { SummaryCard } from "./SummaryCard";

/**
 * Сторож экрана History → Open → Summary.
 *
 * Разбор пишет LLM, и форма полей-списков — обещание модели, а не факт. Живая
 * запись от 2026-07-05 хранит `next_session_focus` ОДНОЙ строкой: NextFocus звал
 * `.join` у строки, React ронял всё дерево, и «Open» давал пустую страницу.
 * Данные ниже повторяют ФОРМУ той записи; сама она приватна и в репозиторий не
 * едет (`data/sessions/` в .gitignore).
 */
afterEach(cleanup);

/** Разбор в том виде, в каком он лежит в базе: поля — как их прислала модель. */
function stored(fields: Record<string, unknown>): Debrief {
  return { overall_summary: "Strong automation story, loose structure.", ...fields } as Debrief;
}

describe("SummaryCard", () => {
  it("next_session_focus строкой — как в живой записи — рисуется, а не роняет экран", () => {
    render(<SummaryCard debrief={stored({ next_session_focus: "Lead with the metric." })} />);

    expect(screen.getByText("Next focus")).toBeTruthy();
    expect(screen.getByText("Lead with the metric.")).toBeTruthy();
  });

  it("next_session_focus списком рисуется через точку", () => {
    render(
      <SummaryCard debrief={stored({ next_session_focus: ["Metrics first", "STAR stories"] })} />,
    );

    expect(screen.getByText("Metrics first · STAR stories")).toBeTruthy();
  });

  it("поля-списки строкой, объектом, null и мусором не роняют экран", () => {
    render(
      <SummaryCard
        debrief={stored({
          strengths: "Reduced the team from five to one.",
          improvements: ["Lead with the impact.", null, 7],
          weak_answers: { question: "Q2", suggested_rephrase: "We cut costs by 40%." },
          vocabulary: "queues",
          consistency_flags: 3,
          next_session_focus: [null, "", {}],
        })}
      />,
    );

    expect(screen.getByText("Reduced the team from five to one.")).toBeTruthy();
    expect(screen.getByText("Lead with the impact.")).toBeTruthy();
    expect(screen.queryByText(/^Fix:/)).toBeNull(); // у голой строки нет fix — нет и подписи
    expect(screen.getByText("“We cut costs by 40%.”")).toBeTruthy();
    expect(screen.queryByText(/Words added/)).toBeNull(); // строка — не запись словаря
    expect(screen.queryByText("Next focus")).toBeNull(); // показывать нечего — секции нет
  });
});
