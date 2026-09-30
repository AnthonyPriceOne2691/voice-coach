import { useEffect, useState } from "react";

import { MicrophoneSetting } from "../components/MicrophoneSetting";
import { api } from "../lib/api";
import type { UserSettings } from "../types/api";

// Коридор темпа — дубль того, что сторожит бэкенд (`orchestrator/pace.py`, doc 15).
// Ползунок не даёт выйти за границы, но правда остаётся на сервере: если он
// ответит 422, мы это ПОКАЖЕМ. Молча разойтись с сервером хуже, чем покраснеть.
const PACE_MIN = 0.85;
const PACE_MAX = 1.6;
const PACE_STEP = 0.05;
const DURATIONS = [15, 30, 45];

function paceWord(value: number): string {
  if (value <= 0.95) return "faster";
  if (value >= 1.45) return "slower";
  return "natural";
}

/** Одна строка настроек: слева что и зачем, справа управление. */
function Setting({
  name,
  hint,
  children,
}: {
  name: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <div className="setting">
      <div className="setting-text">
        <div className="setting-name">{name}</div>
        <div className="setting-hint">{hint}</div>
      </div>
      <div className="setting-control">{children}</div>
    </div>
  );
}

/** Переключатель из нескольких равноправных вариантов. */
function Segmented<T extends string | number | boolean>({
  options,
  value,
  onPick,
}: {
  options: { value: T; label: string }[];
  value: T;
  onPick: (value: T) => void;
}) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button
          key={String(option.value)}
          className={option.value === value ? "on" : ""}
          onClick={() => onPick(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** Ползунок, который шлёт PATCH на ОТПУСКАНИИ: один проезд — один запрос, не сорок. */
function Slider({
  value,
  min,
  max,
  step,
  label,
  onDrag,
  onCommit,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  label: string;
  onDrag: (value: number) => void;
  onCommit: (value: number) => void;
}) {
  const commit = (e: React.SyntheticEvent<HTMLInputElement>) =>
    onCommit(Number(e.currentTarget.value));
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      aria-label={label}
      onChange={(e) => onDrag(Number(e.target.value))}
      onMouseUp={commit}
      onKeyUp={commit}
      onTouchEnd={commit}
    />
  );
}

/** Поля настроек. Отделены от страницы: та отвечает за загрузку и сообщения. */
function SettingsForm({
  settings,
  save,
  drag,
}: {
  settings: UserSettings;
  save: (patch: Partial<UserSettings>) => void;
  drag: (patch: Partial<UserSettings>) => void;
}) {
  return (
    <div className="glass settings">
      <Setting
        name="Speech pace"
        hint="How fast Henry speaks. You can also just say “speak slower” during a session — he will, and the change sticks."
      >
        <Slider
          value={settings.speech_length_scale}
          min={PACE_MIN}
          max={PACE_MAX}
          step={PACE_STEP}
          label="Speech pace"
          onDrag={(v) => drag({ speech_length_scale: v })}
          onCommit={(v) => save({ speech_length_scale: v })}
        />
        <span className="setting-value">
          {settings.speech_length_scale.toFixed(2)}
          <span className="faint">{paceWord(settings.speech_length_scale)}</span>
        </span>
      </Setting>

      <Setting name="Interview length" hint="Henry wraps up when the time is nearly gone.">
        <Segmented
          options={DURATIONS.map((m) => ({ value: m, label: `${m} min` }))}
          value={settings.interview_duration_min}
          onPick={(minutes) => save({ interview_duration_min: minutes })}
        />
      </Setting>

      <Setting
        name="Silence before your turn ends"
        hint="Longer if you pause to think mid-answer; shorter for a faster back-and-forth."
      >
        <Slider
          value={settings.silence_threshold_ms}
          min={800}
          max={3000}
          step={100}
          label="Silence before your turn ends"
          onDrag={(v) => drag({ silence_threshold_ms: v })}
          onCommit={(v) => save({ silence_threshold_ms: v })}
        />
        <span className="setting-value">{(settings.silence_threshold_ms / 1000).toFixed(1)} s</span>
      </Setting>

      <Setting name="Live transcript" hint="Show what was heard while the session runs.">
        <Segmented
          options={[
            { value: true, label: "On" },
            { value: false, label: "Off" },
          ]}
          value={settings.show_live_transcript}
          onPick={(on) => save({ show_live_transcript: on })}
        />
      </Setting>

      <Setting
        name="Microphone"
        hint="Which input Henry listens to. Hit Test and say something — if the bar stays below the mark, he will not hear you. Applies to your next session."
      >
        <MicrophoneSetting
          value={settings.mic_device_id}
          onPick={(deviceId) => save({ mic_device_id: deviceId })}
        />
      </Setting>
    </div>
  );
}

export function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getSettings()
      .then(setSettings)
      .catch(() => setError("Failed to load settings — is the backend running?"));
  }, []);

  const save = async (patch: Partial<UserSettings>) => {
    setError(null);
    try {
      setSettings(await api.patchSettings(patch));
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1600);
    } catch {
      setError("The server rejected that value — it was not saved.");
    }
  };

  // Пока значение едет на сервер, ползунок должен слушаться мыши — иначе он
  // дёргается назад на каждом кадре.
  const drag = (patch: Partial<UserSettings>) =>
    setSettings((prev) => (prev ? { ...prev, ...patch } : prev));

  if (!settings) {
    return error ? (
      <div className="banner banner-error">{error}</div>
    ) : (
      <p className="muted">Loading…</p>
    );
  }

  return (
    <>
      {error && <div className="banner banner-error">{error}</div>}
      {saved && <div className="banner banner-ok">Saved.</div>}

      <h2 className="section-title">Settings</h2>
      <SettingsForm settings={settings} save={(p) => void save(p)} drag={drag} />
    </>
  );
}
