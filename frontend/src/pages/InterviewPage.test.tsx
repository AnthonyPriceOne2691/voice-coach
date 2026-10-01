// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterviewPage } from "./InterviewPage";

// Хук сессии подменён: предмет этих тестов — что страница ПОКАЗЫВАЕТ при данном
// состоянии сессии, а не сам голосовой цикл (его сторожит useVoiceSession.test).
const session = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));
vi.mock("../hooks/useVoiceSession", () => ({ useVoiceSession: () => session.current }));

// jsdom не умеет прокрутку, а TranscriptPanel докручивает ленту в эффекте.
Element.prototype.scrollIntoView = vi.fn();

const HENRY = "Walk me through a tool you built.";
const TRANSCRIPT = [
  { role: "agent", text: HENRY },
  { role: "user", text: "I built a voice pipeline." },
];

function sessionState(active: boolean, transcript: unknown[] = []) {
  return {
    state: active ? "listening" : "idle",
    transcript,
    error: null,
    active,
    micLevel: -Infinity,
    ended: null,
    progress: null,
    startedAt: 0,
    start: vi.fn(),
    end: vi.fn(),
  };
}

/** `GET /settings`: тело с нужным значением переключателя или отказ сети. */
function stubSettings(showLive: boolean | Error) {
  vi.stubGlobal("fetch", () =>
    showLive instanceof Error
      ? Promise.reject(showLive)
      : Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: () =>
            Promise.resolve({
              show_live_transcript: showLive,
              interview_duration_min: 15,
              silence_threshold_ms: 2000,
              speech_length_scale: 1.15,
              mic_device_id: null,
            }),
        }),
  );
}

function renderPage(active: boolean, showLive: boolean | Error) {
  session.current = sessionState(active, TRANSCRIPT);
  stubSettings(showLive);
  render(<InterviewPage reviewTarget={null} onReviewStarted={vi.fn()} />);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/**
 * Сторож на КРЮЧОК, а не на вид.
 *
 * Браузерный стенд (`delivery/evals/browser/stand.py`) начинает прогон с клика по
 * кнопке старта и до 2026-08-17 искал её по ПОДПИСИ («Start Mock Interview»).
 * Переработка интерфейса переименовала кнопку в «Start interview» — стенд четыре
 * дня отчитывался `mic-never-opened`, то есть врал не только про результат, но и
 * про предмет: микрофон был не при чём.
 *
 * Тест сторожит атрибут, от которого стенд теперь зависит. Подпись менять можно —
 * крючок нельзя, и об этом скажет красный тест, а не молчание стенда.
 */
describe("InterviewPage", () => {
  it("кнопка старта несёт крючок для браузерного стенда", () => {
    session.current = sessionState(false);
    stubSettings(true);
    render(<InterviewPage reviewTarget={null} onReviewStarted={vi.fn()} />);

    const start = screen.getByTestId("start-interview"); // R2
    expect(start.tagName).toBe("BUTTON");
    // Подпись проверяется отдельно и мягко: она может меняться, крючок — нет.
    expect(start.textContent?.toLowerCase()).toContain("start");
  });
});

// Переключатель «Live transcript» (doc 17) с 2026-08-13 хранился и показывался на
// экране Settings, а страница его не читала: транскрипт был виден всегда.
describe("InterviewPage · переключатель живого транскрипта", () => {
  it("выключен → во время сессии транскрипта на экране нет", async () => {
    renderPage(true, false); // T1 — repro
    await waitFor(() => expect(screen.queryByText(HENRY)).toBeNull());
  });

  it("включён → транскрипт виден во время сессии", async () => {
    renderPage(true, true); // T2
    expect(await screen.findByText(HENRY)).toBeTruthy();
  });

  it("после конца сессии транскрипт читается и при выключенном переключателе", async () => {
    renderPage(false, false); // T3 — «while the session runs», не после
    expect(await screen.findByText(HENRY)).toBeTruthy();
  });

  it("бэкенд не ответил → умолчание doc 17: транскрипт виден", async () => {
    renderPage(true, new TypeError("Failed to fetch")); // T4
    expect(await screen.findByText(HENRY)).toBeTruthy();
  });
});
