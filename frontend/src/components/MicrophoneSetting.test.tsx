// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MicrophoneSetting } from "./MicrophoneSetting";

const BUILT_IN = { kind: "audioinput", deviceId: "built-in", label: "MacBook Air Microphone" };
const YETI = { kind: "audioinput", deviceId: "yeti", label: "Blue Yeti" };
const SPEAKERS = { kind: "audiooutput", deviceId: "out", label: "MacBook Air Speakers" };

/** Треки живого потока — чтобы видеть, что проверка их погасила. */
function fakeStream() {
  const track = { stop: vi.fn() };
  return { stream: { getTracks: () => [track] } as unknown as MediaStream, track };
}

function stubDevices(
  devices: unknown[],
  getUserMedia = vi.fn(() => Promise.resolve(fakeStream().stream)),
) {
  const enumerateDevices = vi.fn(() => Promise.resolve(devices));
  vi.stubGlobal("navigator", {
    mediaDevices: {
      enumerateDevices,
      getUserMedia,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
  });
  // Полоска уровня считает по настоящему `rmsDbfs`, поэтому «звук» подаётся
  // амплитудой: 0.1 → −20 dBFS, то есть выше порога VAD (−50).
  vi.stubGlobal(
    "AudioContext",
    class {
      createAnalyser() {
        return {
          fftSize: 2048,
          getFloatTimeDomainData: (samples: Float32Array) => samples.fill(0.1),
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
  return { enumerateDevices, getUserMedia };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("MicrophoneSetting", () => {
  it("показывает входы по именам и отмечает сохранённый", async () => {
    stubDevices([BUILT_IN, YETI, SPEAKERS]); // M1
    render(<MicrophoneSetting value="yeti" onPick={vi.fn()} />);

    const select = await screen.findByRole<HTMLSelectElement>("combobox", { name: "Microphone" });
    expect(select.value).toBe("yeti");
    expect(screen.getByRole("option", { name: "Blue Yeti" })).toBeTruthy();
    // Выход в списке входов — обычная ошибка фильтрации, поэтому проверяется.
    expect(screen.queryByRole("option", { name: "MacBook Air Speakers" })).toBeNull();
  });

  it("без разрешения предлагает его выдать, а не показывает безымянный список", async () => {
    const { getUserMedia } = stubDevices([{ ...BUILT_IN, label: "" }]); // M2
    render(<MicrophoneSetting value={null} onPick={vi.fn()} />);

    const allow = await screen.findByRole("button", { name: /Allow microphone access/ });
    fireEvent.click(allow);

    await waitFor(() => expect(getUserMedia).toHaveBeenCalledWith({ audio: true }));
  });

  it("выбор уезжает наружу; «System default» — это null, а не пустая строка", async () => {
    stubDevices([BUILT_IN, YETI]); // M3
    const onPick = vi.fn();
    render(<MicrophoneSetting value={null} onPick={onPick} />);

    const select = await screen.findByRole("combobox", { name: "Microphone" });
    fireEvent.change(select, { target: { value: "yeti" } });
    expect(onPick).toHaveBeenCalledWith("yeti");

    fireEvent.change(select, { target: { value: "" } });
    expect(onPick).toHaveBeenLastCalledWith(null);
  });

  it("сохранённый, но отключённый вход виден отдельной строкой", async () => {
    stubDevices([BUILT_IN]); // сосед M5: экран не должен врать о том, что сохранено
    render(<MicrophoneSetting value="yeti" onPick={vi.fn()} />);

    expect(await screen.findByRole("option", { name: /not connected/ })).toBeTruthy();
  });

  it("Test открывает ВЫБРАННЫЙ вход и показывает уровень, Stop гасит треки", async () => {
    const opened = fakeStream(); // M10
    const { getUserMedia } = stubDevices(
      [BUILT_IN, YETI],
      vi.fn(() => Promise.resolve(opened.stream)),
    );
    render(<MicrophoneSetting value="yeti" onPick={vi.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Test" }));

    await waitFor(() =>
      expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "yeti" } } }),
    );
    // Полоска не просто отрисована — она показывает, что вход слышит.
    expect(await screen.findByText("hearing you")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(opened.track.stop).toHaveBeenCalled());
  });

  it("смена входа во время проверки переносит её на новый", async () => {
    const first = fakeStream(); // M11
    const second = fakeStream();
    const getUserMedia = vi
      .fn()
      .mockResolvedValueOnce(first.stream)
      .mockResolvedValueOnce(second.stream);
    stubDevices([BUILT_IN, YETI], getUserMedia);
    const { rerender } = render(<MicrophoneSetting value="yeti" onPick={vi.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Test" }));
    await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1));

    rerender(<MicrophoneSetting value="built-in" onPick={vi.fn()} />);

    await waitFor(() => expect(first.track.stop).toHaveBeenCalled());
    expect(getUserMedia).toHaveBeenLastCalledWith({ audio: { deviceId: { exact: "built-in" } } });
  });
});
