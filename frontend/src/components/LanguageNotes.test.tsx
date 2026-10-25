// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LanguageNote } from "../types/api";

import { LanguageNotes } from "./LanguageNotes";

const NOTES: LanguageNote[] = [
  {
    turn_index: 1,
    kind: "error",
    said: "I go to the office and meet my client",
    better: "I went to the office and met my client",
    why: "past tense",
    spoken: false,
  },
  {
    turn_index: 3,
    kind: "style",
    said: "the food was very good",
    better: "the food was delicious",
    why: "",
    spoken: false,
  },
];

/** Бэкенд на «Add to Useful Words»: записывает каждый запрос, отвечает заданным. */
function stubAdd(status: number, body: unknown) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${url}`);
      return Promise.resolve({
        ok: status < 400,
        status,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(body),
      });
    }),
  );
  return calls;
}

// Автоочистки нет без `globals: true` (L50): рендеры копились бы в одном документе.
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("LanguageNotes — список «было → лучше» (C10)", () => {
  it("каждая заметка — you said → better — why; оценок нет ни в одной строке", () => {
    render(<LanguageNotes talkId="t1" notes={NOTES} />);

    const [first, second] = screen.getAllByRole("listitem");
    expect(first.textContent).toContain("You said: “I go to the office and meet my client”"); // C10
    expect(first.textContent).toContain("→ I went to the office and met my client — past tense"); // C10
    expect(second.textContent).toContain("→ the food was delicious"); // C10
    expect(second.textContent).not.toContain(" — "); // C10: причины нет — нет и тире
    expect(document.body.textContent).not.toMatch(/score|grade|rating|level|\d\s*\/\s*10/i); // C10
  });

  it("без заметок — честное пустое состояние без кнопок и без похвалы (C10)", () => {
    render(<LanguageNotes talkId="t1" notes={[]} />);

    expect(screen.getByText(/No language notes for this talk/)).toBeTruthy(); // C10
    expect(screen.queryByRole("button")).toBeNull();
    expect(document.body.textContent).not.toMatch(/great|perfect|excellent/i); // C10
  });
});

/**
 * Двойник `new Audio(url)` — КЛАСС, а не стрелка: с vitest 4 стрелку под `new` не
 * зовут, и клик ронял обработчик раньше `play()` — тест краснел чужой причиной (L111).
 */
function stubAudio(onPlay: () => Promise<void>, onPause: () => void = () => undefined) {
  const audio = vi.fn(
    class {
      play = onPlay;
      pause = onPause;
    },
  );
  vi.stubGlobal("Audio", audio);
  return audio;
}

describe("LanguageNotes — Listen (C11)", () => {
  it("проигрывает лучший вариант по адресу своей заметки", () => {
    const play = vi.fn(() => Promise.resolve());
    const audio = stubAudio(play);
    render(<LanguageNotes talkId="t1" notes={NOTES} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Listen" })[1]);

    expect(audio).toHaveBeenCalledWith("/sessions/talks/t1/notes/1/audio"); // C11
    expect(play).toHaveBeenCalledTimes(1); // C11
  });

  it("звук не пошёл — экран говорит об этом, а не молчит", async () => {
    stubAudio(() => Promise.reject(new Error("NotSupportedError")));
    render(<LanguageNotes talkId="t1" notes={NOTES} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Listen" })[0]);

    expect(await screen.findByText("Can't play right now")).toBeTruthy(); // C11
  });

  it("заметки ушли с экрана — фраза смолкла, а не доигрывает в микрофон (C11)", () => {
    const pause = vi.fn();
    stubAudio(() => Promise.resolve(), pause);
    const { unmount } = render(<LanguageNotes talkId="t1" notes={NOTES} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Listen" })[0]);
    expect(pause).not.toHaveBeenCalled(); // C11: пока заметки на экране — звучит

    unmount(); // старт сессии сбрасывает `ended`, смена вкладки снимает страницу
    expect(pause).toHaveBeenCalledTimes(1); // C11: эхо-защита
  });
});

describe("LanguageNotes — Add to Useful Words (C12)", () => {
  it("добавленное — кнопка говорит «добавлено» и больше не жмётся", async () => {
    const calls = stubAdd(200, { status: "added", term_en: "x", translation_ru: "икс" });
    render(<LanguageNotes talkId="t1" notes={NOTES} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Add to Useful Words" })[1]);

    const done = await screen.findByRole("button", { name: "Added to Useful Words" }); // C12
    expect(done).toHaveProperty("disabled", true); // C12: повтор с экрана не уходит
    expect(calls).toEqual(["POST /sessions/talks/t1/notes/1/vocabulary"]); // C12
  });

  it.each([
    [
      200,
      "Already in Useful Words",
      { status: "exists", term_en: "x", translation_ru: "икс" },
      true,
    ],
    [502, "Couldn't add — try again", { detail: "translation failed" }, false],
  ])("ответ %i — кнопка «%s»", async (status, label, body, disabled) => {
    stubAdd(status, body);
    render(<LanguageNotes talkId="t1" notes={NOTES} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Add to Useful Words" })[0]);

    expect(await screen.findByRole("button", { name: label })).toHaveProperty("disabled", disabled); // C12
  });
});
