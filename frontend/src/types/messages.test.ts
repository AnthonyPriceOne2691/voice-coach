import { describe, expect, it } from "vitest";
import { clientMessage, parseServerMessage } from "./messages";

describe("parseServerMessage", () => {
  it("parses a valid state message", () => {
    const message = parseServerMessage(
      JSON.stringify({ type: "state", payload: { value: "listening" } }),
    );
    expect(message).toEqual({ type: "state", payload: { value: "listening" } });
  });

  it("rejects unknown types", () => {
    expect(parseServerMessage(JSON.stringify({ type: "nope", payload: {} }))).toBeNull();
  });

  it("rejects invalid JSON and missing payload", () => {
    expect(parseServerMessage("not json")).toBeNull();
    expect(parseServerMessage(JSON.stringify({ type: "state" }))).toBeNull();
    expect(parseServerMessage(JSON.stringify(42))).toBeNull();
  });
});

describe("clientMessage", () => {
  it("wraps type and payload in the doc 15 envelope", () => {
    expect(JSON.parse(clientMessage("hello"))).toEqual({ type: "hello", payload: {} });
    expect(JSON.parse(clientMessage("utterance_end", { audio_base64: "aaa" }))).toEqual({
      type: "utterance_end",
      payload: { audio_base64: "aaa" },
    });
  });
});
