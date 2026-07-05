import { describe, expect, it } from "vitest";
import { formatDate, formatDuration, turnTimestamp } from "./format";

describe("formatDuration", () => {
  it("handles null and minutes+seconds", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(59)).toBe("59 s");
    expect(formatDuration(125)).toBe("2 min 5 s");
    expect(formatDuration(120)).toBe("2 min");
  });
});

describe("formatDate", () => {
  it("falls back gracefully", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatDate("2026-07-05T10:00:00Z")).toMatch(/Jul/);
  });
});

describe("turnTimestamp", () => {
  it("renders mm:ss", () => {
    expect(turnTimestamp(0)).toBe("00:00");
    expect(turnTimestamp(75_000)).toBe("01:15");
  });
});
