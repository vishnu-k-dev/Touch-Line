/**
 * Heatmap colour: any visited square shows, quiet squares stay amber, and the busiest go hot red.
 * Opacity rises faster than colour so busy squares are solid while quiet ones fade back into the grass.
 */
export function heatColor(value: number, max: number): { fill: string; opacity: number } {
  const raw = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  const hue = Math.round(40 - 40 * raw); // 40 = amber (yellow turns olive over grass), 0 = red
  const lightness = Math.round(56 - 10 * raw);
  return { fill: `hsl(${hue} 100% ${lightness}%)`, opacity: Math.round((0.2 + 0.78 * Math.pow(raw, 0.8)) * 100) / 100 };
}

/** The legend bar, built from the same ramp so it always matches the map. */
export const HEAT_LEGEND = `linear-gradient(90deg, ${[0, 0.25, 0.5, 0.75, 1]
  .map((t) => {
    const { fill, opacity } = heatColor(t, 1);
    return `${fill.replace(")", ` / ${opacity})`)} ${t * 100}%`;
  })
  .join(", ")})`;
