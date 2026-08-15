import { afterEach, describe, expect, it, vi } from "vitest";

import { labelsHidden, listMicrophones, openMicrophone, requestMicAccess } from "./mic";

/** Ошибка железа приходит не `Error`-ом, а объектом со своим `name`. */
function domError(name: string): Error {
  const error = new Error(name);
  error.name = name;
  return error;
}

function fakeStream(): MediaStream {
  const track = { stop: vi.fn() };
  return { getTracks: () => [track] } as unknown as MediaStream;
}

interface Media {
  getUserMedia: ReturnType<typeof vi.fn>;
  enumerateDevices: ReturnType<typeof vi.fn>;
}

function mockMediaDevices(getUserMedia: Media["getUserMedia"], devices: unknown[] = []): Media {
  const media: Media = { getUserMedia, enumerateDevices: vi.fn(() => Promise.resolve(devices)) };
  vi.stubGlobal("navigator", { mediaDevices: media });
  return media;
}

afterEach(() => vi.unstubAllGlobals());

describe("listMicrophones / labelsHidden", () => {
  it("оставляет только входы", async () => {
    // M1: список — это входы; выход, попавший в него, выбирать нечем.
    mockMediaDevices(vi.fn(), [
      { kind: "audioinput", deviceId: "in-1", label: "MacBook Air Microphone" },
      { kind: "audiooutput", deviceId: "out-1", label: "MacBook Air Speakers" },
      { kind: "videoinput", deviceId: "cam-1", label: "FaceTime HD" },
    ]);

    expect(await listMicrophones()).toEqual([
      { deviceId: "in-1", label: "MacBook Air Microphone" },
    ]);
  });

  it("пустые имена и пустой список одинаково значат «нет разрешения»", () => {
    // M2: признак «имена скрыты» — то, по чему экран решает показать приглашение.
    expect(labelsHidden([{ deviceId: "in-1", label: "" }])).toBe(true);
    expect(labelsHidden([])).toBe(true);
    expect(labelsHidden([{ deviceId: "in-1", label: "Yeti" }])).toBe(false);
  });
});

describe("requestMicAccess", () => {
  it("гасит поток сразу же: разрешение нужно ради имён, а не ради записи", async () => {
    // M2: приглашение выдать доступ не должно оставлять микрофон открытым.
    const stream = fakeStream();
    mockMediaDevices(vi.fn(() => Promise.resolve(stream)));

    await requestMicAccess();

    expect(stream.getTracks()[0].stop).toHaveBeenCalled();
  });
});

describe("openMicrophone", () => {
  it("без выбора открывает системный вход по умолчанию", async () => {
    const getUserMedia = vi.fn(() => Promise.resolve(fakeStream())); // M6
    mockMediaDevices(getUserMedia);

    const opened = await openMicrophone(null);

    expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(opened.fellBackToDefault).toBe(false);
  });

  it("выбранный вход запрашивается как exact, а не как пожелание", async () => {
    const getUserMedia = vi.fn(() => Promise.resolve(fakeStream())); // M4
    mockMediaDevices(getUserMedia);

    await openMicrophone("abc123");

    // `ideal` открыл бы ДРУГОЙ микрофон молча — вся поставка про то, чтобы этого
    // не происходило, поэтому проверяется именно форма constraint'а.
    expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "abc123" } } });
  });

  it("пропажа устройства — фолбэк на системный, но с флагом", async () => {
    const getUserMedia = vi // M5
      .fn()
      .mockRejectedValueOnce(domError("OverconstrainedError"))
      .mockResolvedValueOnce(fakeStream());
    mockMediaDevices(getUserMedia);

    const opened = await openMicrophone("gone");

    expect(opened.fellBackToDefault).toBe(true);
    expect(getUserMedia).toHaveBeenLastCalledWith({ audio: true });
  });

  it("то же для NotFoundError", async () => {
    // M5: вторая формулировка того же «устройства нет» у другого браузера.
    const getUserMedia = vi
      .fn()
      .mockRejectedValueOnce(domError("NotFoundError"))
      .mockResolvedValueOnce(fakeStream());
    mockMediaDevices(getUserMedia);

    expect((await openMicrophone("gone")).fellBackToDefault).toBe(true);
  });

  it("отказ в доступе НЕ подменяется фолбэком", async () => {
    // M12: «нет доступа» и «нет устройства» лечатся по-разному.
    const getUserMedia = vi.fn().mockRejectedValue(domError("NotAllowedError"));
    mockMediaDevices(getUserMedia);

    // Иначе причина «человек не дал доступ» превратилась бы в «устройство
    // пропало», и лечили бы не то.
    await expect(openMicrophone("abc123")).rejects.toThrow("NotAllowedError");
    expect(getUserMedia).toHaveBeenCalledTimes(1);
  });
});
