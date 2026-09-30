// Client-side VAD: RMS level + end-of-utterance state machine (doc 03 MVP parameters).

export const SILENCE_THRESHOLD_DBFS = -50; // re-tuned after live test: -45 missed quiet speech
export const DEFAULT_SILENCE_MS = 2000; // raised from 1200 on 2026-09-07: 1.2 s cut off mid-sentence pauses
export const MIN_UTTERANCE_MS = 700;

/** RMS level in dBFS from AnalyserNode float time-domain data (range -1..1). */
export function rmsDbfs(samples: Float32Array): number {
  if (samples.length === 0) return -Infinity;
  let sumSquares = 0;
  for (const sample of samples) {
    sumSquares += sample * sample;
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
