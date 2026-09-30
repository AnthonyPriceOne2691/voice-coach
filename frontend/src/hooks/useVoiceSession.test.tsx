// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useVoiceSession } from "./useVoiceSession";

// Сторож связки, а не поведения устройства: `openMicrophone` проверен отдельно
// (`lib/mic.test.ts`), а здесь важно, что настройка вообще ДОЕЗЖАЕТ до старта.
// Без этого теста ключ мог бы честно храниться, отдаваться и валидироваться —
// и не влиять ни на что, а увидеть это можно было бы только ухом.

const SETTINGS = {
  show_live_transcript: true,
  interview_duration_min: 15,
  silence_threshold_ms: 2000,
  speech_length_scale: 1.15,
  mic_device_id: "saved-mic",
};

function domError(name: string): Error {
  const error = new Error(name);
  error.name = name;
  return error;
}

function stubEnvironment(getUserMedia: ReturnType<typeof vi.fn>) {
  vi.stubGlobal("fetch", () =>
    Promise.resolve({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve(SETTINGS),
    }),
  );
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  vi.stubGlobal(
    "AudioContext",
    class {
      createAnalyser() {
        return { fftSize: 2048, getFloatTimeDomainData: () => undefined };
      }
      createMediaStreamSource() {
        return { connect: () => undefined };
      }
      close() {
        return Promise.resolve();
      }
    },
  );
  vi.stubGlobal(
    "WebSocket",
    class {
      onmessage: unknown = null;
      onopen: unknown = null;
      onerror: unknown = null;
      onclose: unknown = null;
      send = () => undefined;
      close = () => undefined;
    },
  );
}

function fakeStream(): MediaStream {
  return { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("useVoiceSession · выбранный микрофон", () => {
  it("сессия стартует на сохранённом входе", async () => {
    const getUserMedia = vi.fn(() => Promise.resolve(fakeStream())); // M4
    stubEnvironment(getUserMedia);
    const { result } = renderHook(() => useVoiceSession());

    await act(() => result.current.start());

    expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "saved-mic" } } });
    expect(result.current.error).toBeNull();
    act(() => result.current.end());
  });

  it("пропажа входа не отменяет сессию, но и не молчит", async () => {
    const getUserMedia = vi // M5
      .fn()
      .mockRejectedValueOnce(domError("OverconstrainedError"))
      .mockResolvedValueOnce(fakeStream());
    stubEnvironment(getUserMedia);
    const { result } = renderHook(() => useVoiceSession());

    await act(() => result.current.start());

    await waitFor(() => expect(result.current.error).toMatch(/not available/));
    expect(result.current.active).toBe(true);
    act(() => result.current.end());
  });
});
