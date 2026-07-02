import { describe, expect, it } from "vitest";
import { SILENCE_THRESHOLD_DBFS, SilenceDetector, rmsDbfs } from "./vad";

function samplesAt(amplitude: number): Float32Array {
  // Constant amplitude => deterministic RMS (float domain, -1..1)
  return new Float32Array(64).fill(amplitude);
}

describe("rmsDbfs", () => {
  it("returns -Infinity for pure silence", () => {
    expect(rmsDbfs(samplesAt(0))).toBe(-Infinity);
  });

  it("returns 0 dBFS for full-scale signal", () => {
    expect(rmsDbfs(samplesAt(1))).toBeCloseTo(0, 5);
  });

  it("quiet noise is below the threshold, quiet speech is above", () => {
    expect(rmsDbfs(samplesAt(0.001))).toBeLessThan(SILENCE_THRESHOLD_DBFS); // -60 dBFS
    expect(rmsDbfs(samplesAt(0.01))).toBeGreaterThan(SILENCE_THRESHOLD_DBFS); // -40 dBFS
  });
});

describe("SilenceDetector", () => {
  const LOUD = -20;
  const QUIET = -60;

  it("stays idle on silence", () => {
    const detector = new SilenceDetector();
    expect(detector.update(QUIET, 0)).toBe("idle");
    expect(detector.update(QUIET, 5000)).toBe("idle");
  });

  it("emits utterance_end after 1.2s of silence following speech", () => {
    const detector = new SilenceDetector();
    expect(detector.update(LOUD, 0)).toBe("speaking");
    expect(detector.update(LOUD, 1000)).toBe("speaking");
    expect(detector.update(QUIET, 1500)).toBe("speaking"); // silence too short
    expect(detector.update(QUIET, 2100)).toBe("speaking");
    expect(detector.update(QUIET, 2300)).toBe("utterance_end"); // >= 1200ms quiet
  });

  it("discards utterances shorter than 700ms as noise", () => {
    const detector = new SilenceDetector();
    detector.update(LOUD, 0);
    detector.update(LOUD, 300); // only 300ms of speech
    expect(detector.update(QUIET, 1600)).toBe("discarded");
  });

  it("resets after utterance_end and can detect the next one", () => {
    const detector = new SilenceDetector();
    detector.update(LOUD, 0);
    detector.update(LOUD, 1000);
    expect(detector.update(QUIET, 2300)).toBe("utterance_end");
    expect(detector.update(QUIET, 2400)).toBe("idle");
    expect(detector.update(LOUD, 2500)).toBe("speaking");
  });
});
