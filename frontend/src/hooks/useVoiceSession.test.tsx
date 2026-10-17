// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useVoiceSession } from "./useVoiceSession";

// Сторож связки, а не поведения устройства: `openMicrophone` проверен отдельно
// (`lib/mic.test.ts`), а здесь важно, что настройка вообще ДОЕЗЖАЕТ до старта.
// Без этого теста ключ мог бы честно храниться, отдаваться и валидироваться —
// и не влиять ни на что, а увидеть это можно было бы только ухом.
// Ровно так и жил порог тишины: сторож стоял на микрофон, а соседний ключ с
// 2026-08-13 до VAD не доезжал (поставка vad-silence-setting). Сторож нужен
// КАЖДОМУ ключу, который обещает менять поведение, а не первому попавшемуся.

const SETTINGS = {
  show_live_transcript: true,
  interview_duration_min: 15,
  silence_threshold_ms: 2000,
  speech_length_scale: 1.15,
  mic_device_id: "saved-mic",
};

/** Ответ `GET /settings`: тело или отказ сети. */
type SettingsResponder = () => Promise<unknown>;

interface FakeSocket {
  onmessage: ((event: { data: string }) => void) | null;
}

let socket: FakeSocket | null = null;
/** Типы сообщений, которые хук отправил серверу, по порядку. */
let sent: string[] = [];

function domError(name: string): Error {
  const error = new Error(name);
  error.name = name;
  return error;
}

function stubEnvironment(
  getUserMedia: ReturnType<typeof vi.fn>,
  settings: SettingsResponder = () => Promise.resolve(SETTINGS),
  level = { value: 0 }, // амплитуда, которую «слышит» анализатор
) {
  vi.stubGlobal("fetch", () =>
    settings().then((body) => ({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve(body),
    })),
  );
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  vi.stubGlobal(
    "AudioContext",
    class {
      createAnalyser() {
        return {
          fftSize: 2048,
          getFloatTimeDomainData: (samples: Float32Array) => samples.fill(level.value),
        };
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
      send = (data: string) => {
        sent.push((JSON.parse(data) as { type: string }).type);
      };
      close = () => undefined;
      constructor() {
        socket = this as unknown as FakeSocket;
      }
    },
  );
}

function fakeStream(): MediaStream {
  return { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream;
}

const LOUD = 0.1; // RMS 0.1 ≈ −20 dBFS — громче порога VAD (−50 dBFS)
const QUIET = 0;
const POLL_MS = 50; // шаг опроса VAD в хуке

/**
 * Сессия, которая слушает: сервер прислал `listening`, запись идёт. Опрос VAD
 * сам не крутится — его шаги и часы двигает `run`, поэтому граница порога
 * проверяется с точностью до одного опроса, а не «примерно через две секунды».
 */
async function listeningSession(settings: SettingsResponder, level: { value: number }) {
  let poll: () => void = () => undefined;
  let clock = 0;
  vi.spyOn(window, "setInterval").mockImplementation((handler: TimerHandler) => {
    poll = handler as () => void;
    return 1;
  });
  vi.spyOn(performance, "now").mockImplementation(() => clock);
  const stop = vi.fn(); // конец хода = остановка записи
  vi.stubGlobal(
    "MediaRecorder",
    class {
      state = "inactive";
      start() {
        this.state = "recording";
      }
      stop() {
        this.state = "inactive";
        stop();
      }
    },
  );
  stubEnvironment(
    vi.fn(() => Promise.resolve(fakeStream())),
    settings,
    level,
  );
  const { result } = renderHook(() => useVoiceSession());
  await act(() => result.current.start());
  const listening = JSON.stringify({ type: "state", payload: { value: "listening" } });
  act(() => socket?.onmessage?.({ data: listening }));
  const run = (ms: number) =>
    act(() => {
      for (let elapsed = 0; elapsed < ms; elapsed += POLL_MS) {
        clock += POLL_MS;
        poll();
      }
    });
  return { stop, run };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  socket = null;
  sent = [];
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

describe("useVoiceSession · порог тишины из Settings", () => {
  it.each([
    {
      // R1 — repro: до правки ход кончался через 2 s при любом значении ползунка
      name: "сохранённые 0.9 s",
      settings: () => Promise.resolve({ ...SETTINGS, silence_threshold_ms: 900 }),
      silenceMs: 900,
    },
    {
      // R2 — настройки не условие старта, как и выбор входа
      name: "бэкенд не ответил",
      settings: () => Promise.reject(new TypeError("Failed to fetch")),
      silenceMs: 2000,
    },
    {
      // R3 — NaN в детекторе оборвал бы каждую фразу на первом тихом опросе
      name: "в базе не число",
      settings: () => Promise.resolve({ ...SETTINGS, silence_threshold_ms: "2s" }),
      silenceMs: 2000,
    },
  ])("$name → ход кончается через $silenceMs мс тишины", async ({ settings, silenceMs }) => {
    const level = { value: LOUD };
    const vad = await listeningSession(settings, level);
    vad.run(1000); // фраза длиннее минимальной реплики (700 мс)
    level.value = QUIET;

    vad.run(silenceMs - POLL_MS);
    expect(vad.stop).not.toHaveBeenCalled();
    vad.run(POLL_MS);
    expect(vad.stop).toHaveBeenCalledTimes(1);
  });
});

describe("useVoiceSession · вид сессии выбирает стартовое сообщение", () => {
  it.each([
    { name: "интервью — по умолчанию", mode: undefined, first: "start_interview" },
    { name: "разговор (T1)", mode: { kind: "talk" } as const, first: "start_talk" },
    {
      name: "разбор",
      mode: { kind: "review", interviewId: "int-1" } as const,
      first: "start_review",
    },
  ])("$name → $first", async ({ mode, first }) => {
    stubEnvironment(vi.fn(() => Promise.resolve(fakeStream())));
    const { result } = renderHook(() => useVoiceSession());

    await act(() => result.current.start(mode));
    act(() => (socket as unknown as { onopen: () => void }).onopen());

    expect(sent).toEqual(["hello", first]);
    act(() => result.current.end());
  });
});
