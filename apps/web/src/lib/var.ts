/**
 * The analyst's number check, as the About page demonstrates it. This mirrors `_supported` in
 * apps/api/app/agents/analyst.py: a claimed number passes if it equals a number in the cited tool result (to two
 * decimals), or is the difference or sum of two of them.
 */
const TOLERANCE = 0.0051;

export type VarVerdict = { ok: true; kind: "direct" | "derived"; detail: string } | { ok: false; detail: string };

export function varCheck(value: number, numbers: number[]): VarVerdict {
  const uniq = [...new Set(numbers.map((n) => Math.round(n * 1e4) / 1e4))];
  const direct = uniq.find((n) => Math.abs(value - n) <= TOLERANCE);
  if (direct !== undefined) return { ok: true, kind: "direct", detail: `${direct} appears in the cited tool result.` };
  for (const a of uniq) {
    for (const b of uniq) {
      if (Math.abs(value - (a + b)) <= TOLERANCE) return { ok: true, kind: "derived", detail: `${value} = ${a} + ${b}, both from the cited tool result.` };
      if (a > b && Math.abs(value - (a - b)) <= TOLERANCE) return { ok: true, kind: "derived", detail: `${value} = ${a} − ${b}, both from the cited tool result.` };
    }
  }
  return { ok: false, detail: `${value} does not appear in the cited tool results.` };
}
