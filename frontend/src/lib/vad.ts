// Client-side VAD: RMS level + end-of-utterance state machine (doc 03 MVP parameters).

export const SILENCE_THRESHOLD_DBFS = -45;
export const DEFAULT_SILENCE_MS = 1200;
export const MIN_UTTERANCE_MS = 700;

/** RMS level in dBFS from AnalyserNode byte time-domain data (128 = zero signal). */
export function rmsDbfs(samples: Uint8Array): number {
  if (samples.length === 0) return -Infinity;
  let sumSquares = 0;
  for (const sample of samples) {
    const normalized = (sample - 128) / 128;
    sumSquares += normalized * normalized;
  }
  const rms = Math.sqrt(sumSquares / samples.length);
  return rms === 0 ? -Infinity : 20 * Math.log10(rms);
}

export type VadEvent = "idle" | "speaking" | "utterance_end" | "discarded";

/**
 * End-of-utterance detector: speech starts above threshold; `silenceMs` of quiet ends it.
 * Utterances shorter than `minUtteranceMs` are discarded as noise.
 */
export class SilenceDetector {
  private speechStartMs: number | null = null;
  private lastLoudMs = 0;

  constructor(
    private readonly opts = {
      thresholdDbfs: SILENCE_THRESHOLD_DBFS,
      silenceMs: DEFAULT_SILENCE_MS,
      minUtteranceMs: MIN_UTTERANCE_MS,
    },
  ) {}

  update(dbfs: number, nowMs: number): VadEvent {
    const loud = dbfs > this.opts.thresholdDbfs;
    if (this.speechStartMs === null) {
      if (!loud) return "idle";
      this.speechStartMs = nowMs;
      this.lastLoudMs = nowMs;
      return "speaking";
    }
    if (loud) {
      this.lastLoudMs = nowMs;
      return "speaking";
    }
    if (nowMs - this.lastLoudMs < this.opts.silenceMs) return "speaking";
    const duration = this.lastLoudMs - this.speechStartMs;
    this.reset();
    return duration >= this.opts.minUtteranceMs ? "utterance_end" : "discarded";
  }

  reset(): void {
    this.speechStartMs = null;
    this.lastLoudMs = 0;
  }
}
