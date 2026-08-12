// Pure display helpers (vitest-covered).

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return minutes > 0 ? `${minutes} min ${rest ? `${rest} s` : ""}`.trim() : `${rest} s`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function turnTimestamp(ms: number): string {
  const total = Math.floor(ms / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/** Строка «когда шла сессия» для History.
 *
 * Различает закрытую сессию и брошенную по `ended_at`, а НЕ по длительности:
 * `duration_sec` пишется при каждом flush хода, то есть заполнен и у сессии,
 * которую бросили посреди ответа. До 2026-08-12 строка показывала начало и
 * длительность, и эти два состояния были на экране неотличимы.
 *
 * У брошенной сессии длительность не показывается совсем: число есть, но
 * итогом оно не является, а пустое место читалось бы как «данных нет».
 *
 * Текст английский, как весь остальной интерфейс: комментарии в коде русские,
 * строки на экране — нет. Поймано снимком экрана, а не тестом.
 */
export function formatSessionSpan(
  startedAt: string | null | undefined,
  endedAt: string | null | undefined,
  durationSec: number | null | undefined,
): string {
  const start = formatDate(startedAt);
  if (!endedAt) return `${start} · not finished`;
  return `${start} → ${formatDate(endedAt)} · ${formatDuration(durationSec)}`;
}
