/** A tiny football: pentagon in the middle, seams out to the edge. */
export function BallMark({ size = 28 }: { size?: number }) {
  const pent = [
    [16, 10.2],
    [21.5, 14.2],
    [19.4, 20.6],
    [12.6, 20.6],
    [10.5, 14.2],
  ];
  const rim = [
    [16, 2.4],
    [28.3, 11.4],
    [23.6, 25.8],
    [8.4, 25.8],
    [3.7, 11.4],
  ];
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden>
      <circle cx="16" cy="16" r="14.2" fill="var(--surface)" stroke="var(--fg)" strokeWidth="1.6" />
      {pent.map(([x, y], i) => (
        <line key={i} x1={x} y1={y} x2={rim[i][0]} y2={rim[i][1]} stroke="var(--fg)" strokeWidth="1.3" />
      ))}
      <polygon points={pent.map((p) => p.join(",")).join(" ")} fill="var(--fg)" />
    </svg>
  );
}
