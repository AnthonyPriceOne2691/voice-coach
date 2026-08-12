import { describe, expect, it } from "vitest";
import { formatDate, formatDuration, formatSessionSpan, turnTimestamp } from "./format";

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

describe("формат строки History отличает закрытую сессию от брошенной", () => {
  // D1/D2. До правки строка показывала только начало и длительность, а
  // duration_sec заполнен у ОБЕИХ: он пишется при каждом flush хода, то есть
  // означает «последний записанный момент», а не конец сессии. По списку
  // History брошенную сессию от закрытой было не отличить.
  it("закрытая сессия показывает время окончания", () => {
    expect(formatSessionSpan("2026-08-12T13:33:22+00:00", "2026-08-12T13:33:55+00:00", 34)).toMatch(
      /→/,
    ); // D1
  });

  it("брошенная сессия названа словами (по-английски, как весь UI)", () => {
    const span = formatSessionSpan("2026-08-12T10:44:37+00:00", null, 33); // D2
    expect(span).toMatch(/not finished/i); // D2
    expect(span).not.toMatch(/33/); // D2 — число есть, но итогом не притворяется
  });
});
