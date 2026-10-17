// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TalkPage } from "./TalkPage";

// Хук сессии подменён: предмет — что страница ПОКАЗЫВАЕТ и что она просит у хука,
// а не сам голосовой цикл (его сторожит useVoiceSession.test).
const session = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));
vi.mock("../hooks/useVoiceSession", () => ({ useVoiceSession: () => session.current }));

// jsdom не умеет прокрутку, а TranscriptPanel докручивает ленту в эффекте (L71).
Element.prototype.scrollIntoView = vi.fn();

const HENRY = "So, how's your day going so far?";

function renderTalk(active: boolean, showLive: boolean) {
  const start = vi.fn();
  session.current = {
    state: active ? "listening" : "idle",
    transcript: [
      { role: "agent", text: HENRY },
      { role: "user", text: "Pretty good, thanks." },
    ],
    error: null,
    active,
    micLevel: -Infinity,
    ended: null,
    progress: null,
    startedAt: 0,
    start,
    end: vi.fn(),
  };
  vi.stubGlobal("fetch", () =>
    Promise.resolve({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve({ show_live_transcript: showLive }),
    }),
  );
  render(<TalkPage />);
  return start;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TalkPage", () => {
  it("кнопка Start начинает именно разговор и несёт крючок для стенда (T1)", () => {
    const start = renderTalk(false, true);

    const button = screen.getByTestId("start-talk");
    fireEvent.click(button);

    expect(start).toHaveBeenCalledWith({ kind: "talk" });
  });

  it("во время разговора шапка говорит о разговоре, а не об интервью (T1)", async () => {
    renderTalk(true, true);

    expect(screen.getByText("Talk with Henry")).toBeTruthy();
    expect(screen.queryByText("Mock interview with Henry")).toBeNull();
    expect(await screen.findByText(HENRY)).toBeTruthy();
  });

  it("Live transcript выключен → во время разговора пузырей нет, после — есть (T1)", async () => {
    renderTalk(true, false);
    await waitFor(() => expect(screen.queryByText(HENRY)).toBeNull());

    cleanup();
    renderTalk(false, false);
    expect(await screen.findByText(HENRY)).toBeTruthy();
  });
});
