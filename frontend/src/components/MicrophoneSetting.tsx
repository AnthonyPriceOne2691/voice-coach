import { useCallback, useEffect, useState } from "react";

import { useMicLevel } from "../hooks/useMicLevel";
import { labelsHidden, listMicrophones, requestMicAccess, type MicDevice } from "../lib/mic";

import { MicLevelMeter } from "./MicLevelMeter";

// Пустая строка = «системный по умолчанию»: у `<option>` значение обязано быть
// строкой, а наружу и в базу уезжает `null`.
const SYSTEM_DEFAULT = "";
const BLOCKED = "Access was blocked. Allow the microphone for this site in the browser.";

interface Props {
  value: string | null;
  onPick: (deviceId: string | null) => void;
}

/** Список входов + разрешение + живая проверка уровня. */
export function MicrophoneSetting({ value, onPick }: Props) {
  const [devices, setDevices] = useState<MicDevice[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [testing, setTesting] = useState(false);
  const { level, problem } = useMicLevel(value, testing);

  const refresh = useCallback(
    () =>
      listMicrophones()
        .then(setDevices)
        .catch(() => setDevices([]))
        .finally(() => setLoaded(true)),
    [],
  );

  useEffect(() => {
    void refresh();
    // Железо подключают и отключают при открытом экране — список обязан жить.
    const media: MediaDevices | undefined = navigator.mediaDevices;
    const onChange = () => void refresh();
    media?.addEventListener?.("devicechange", onChange);
    return () => media?.removeEventListener?.("devicechange", onChange);
  }, [refresh]);

  const allow = () =>
    requestMicAccess()
      .then(refresh)
      .catch(() => setBlocked(true));

  if (!loaded) return <span className="faint">…</span>;

  // Имена скрыты, пока нет разрешения. Показывать список из «Microphone 1,
  // Microphone 2» бессмысленно — выбирать не из чего.
  if (labelsHidden(devices)) {
    return (
      <div className="mic-picker">
        <button className="btn btn-quiet" onClick={() => void allow()}>
          Allow microphone access
        </button>
        {blocked && <div className="mic-picker-note">{BLOCKED}</div>}
      </div>
    );
  }

  // Сохранённый вход, которого сейчас нет, показывается ОТДЕЛЬНОЙ строкой:
  // иначе список молча показывал бы «System default» при другом значении в базе,
  // то есть экран врал бы о том, что сохранено.
  const missing = value !== null && !devices.some((d) => d.deviceId === value);

  return (
    <div className="mic-picker">
      <div className="mic-picker-row">
        <select
          aria-label="Microphone"
          value={value ?? SYSTEM_DEFAULT}
          onChange={(e) => onPick(e.target.value || null)}
        >
          <option value={SYSTEM_DEFAULT}>System default</option>
          {devices.map((device) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label}
            </option>
          ))}
          {missing && <option value={value}>Saved microphone — not connected</option>}
        </select>
        <button className="btn btn-quiet" onClick={() => setTesting((on) => !on)}>
          {testing ? "Stop" : "Test"}
        </button>
      </div>
      {testing && <MicLevelMeter level={level} />}
      {problem && <div className="mic-picker-note">{problem}</div>}
    </div>
  );
}
