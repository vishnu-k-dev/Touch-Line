import { describe, expect, it } from "vitest";
import { HEAT_LEGEND, heatColor } from "./heat";

const hue = (fill: string) => Number(/hsl\((\d+)/.exec(fill)![1]);

describe("heatColor", () => {
  it("is hot red at the maximum and amber for a little", () => {
    expect(hue(heatColor(54, 54).fill)).toBe(0); // red
    expect(hue(heatColor(1, 54).fill)).toBeGreaterThan(30); // amber, not red and not green
    expect(hue(heatColor(1, 54).fill)).toBeLessThanOrEqual(40);
  });
  it("never produces green: hue stays between red and amber", () => {
    for (let v = 0; v <= 54; v++) expect(hue(heatColor(v, 54).fill)).toBeLessThanOrEqual(40);
  });
  it("gets redder and more opaque as the count rises", () => {
    let lastHue = 99;
    let lastOpacity = 0;
    for (const v of [1, 5, 15, 30, 54]) {
      const { fill, opacity } = heatColor(v, 54);
      expect(hue(fill)).toBeLessThanOrEqual(lastHue);
      expect(opacity).toBeGreaterThan(lastOpacity);
      [lastHue, lastOpacity] = [hue(fill), opacity];
    }
  });
  it("copes with an empty map and clamps values above the max", () => {
    expect(heatColor(0, 0).opacity).toBeGreaterThan(0);
    expect(heatColor(99, 54)).toEqual(heatColor(54, 54));
  });
  it("builds a legend from the same ramp", () => {
    expect(HEAT_LEGEND).toContain("hsl(0 100%");
    expect(HEAT_LEGEND.startsWith("linear-gradient(90deg")).toBe(true);
  });
});
