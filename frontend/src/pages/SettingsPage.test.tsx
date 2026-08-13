// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";

const SETTINGS = {
  show_live_transcript: true,
  interview_duration_min: 15,
  silence_threshold_ms: 1200,
  speech_length_scale: 1.15,
};

function mockFetch(patchResponse?: { ok: boolean; status: number }) {
  const calls: { url: string; method: string; body?: string }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      calls.push({ url, method, body: init?.body as string | undefined });
      const failed = method === "PATCH" && patchResponse && !patchResponse.ok;
      return Promise.resolve({
        ok: !failed,
        status: failed ? patchResponse.status : 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(SETTINGS),
      });
    }),
  );
  return calls;
}

// Автоочистки нет: она включается только с `globals: true`, а конфиг проекта
// оставлен без глобалей. Без этой строки рендеры копятся в одном документе, и
// запросы находят по несколько ползунков — тест падает не на своём предмете.
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SettingsPage", () => {
  it("показывает значение, пришедшее с сервера", async () => {
    mockFetch();
    render(<SettingsPage />);

    const slider = await screen.findByRole<HTMLInputElement>("slider", { name: "Speech pace" }); // S2
    expect(slider.value).toBe("1.15");
    expect(screen.getByText("natural")).toBeTruthy();
  });

  it("шлёт один PATCH на отпускание, а не на каждое движение", async () => {
    const calls = mockFetch();
    render(<SettingsPage />);
    const slider = await screen.findByRole<HTMLInputElement>("slider", { name: "Speech pace" });

    // S3: три «кадра» перетаскивания и одно отпускание
    fireEvent.change(slider, { target: { value: "1.25" } });
    fireEvent.change(slider, { target: { value: "1.35" } });
    fireEvent.change(slider, { target: { value: "1.45" } });
    fireEvent.mouseUp(slider, { target: { value: "1.45" } });

    await waitFor(() => expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(1));
    expect(calls.at(-1)?.body).toContain("1.45");
  });

  it("показывает, что сервер отверг значение", async () => {
    mockFetch({ ok: false, status: 422 });
    render(<SettingsPage />);
    const slider = await screen.findByRole<HTMLInputElement>("slider", { name: "Speech pace" });

    fireEvent.mouseUp(slider, { target: { value: "1.45" } }); // S4

    expect(await screen.findByText(/rejected that value/)).toBeTruthy();
  });
});
