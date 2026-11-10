import { describe, expect, it } from "vitest";
import { varCheck } from "./var";

const RESULT = [1, 15, 2.49, 2, 3, 0.15];

describe("varCheck (the About page demo of the analyst's number check)", () => {
  it("lets a number through when it appears in the tool result", () => {
    expect(varCheck(2.49, RESULT)).toMatchObject({ ok: true, kind: "direct" });
    expect(varCheck(15, RESULT)).toMatchObject({ ok: true, kind: "direct" });
  });
  it("tolerates rounding to two decimals", () => {
    expect(varCheck(2.4899, RESULT).ok).toBe(true);
    expect(varCheck(2.5, RESULT).ok).toBe(false);
  });
  it("allows a difference or sum of two source numbers, and says where it came from", () => {
    expect(varCheck(2.34, RESULT)).toMatchObject({ ok: true, kind: "derived" });
    expect(varCheck(2.34, RESULT).detail).toContain("2.49 − 0.15");
    expect(varCheck(18, RESULT)).toMatchObject({ ok: true, kind: "derived" }); // 15 + 3
  });
  it("rejects a made-up number with the real system's wording", () => {
    const v = varCheck(3.5, RESULT);
    expect(v.ok).toBe(false);
    expect(v.detail).toBe("3.5 does not appear in the cited tool results.");
  });
});
