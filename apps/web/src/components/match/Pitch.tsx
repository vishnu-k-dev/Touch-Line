import type { ReactNode } from "react";

/** StatsBomb pitch: 120 x 80, every team attacks toward x=120. */
export function PitchLines() {
  return (
    <g fill="none" stroke="var(--pitch-line)" strokeWidth={0.45}>
      <rect x={0} y={0} width={120} height={80} />
      <line x1={60} y1={0} x2={60} y2={80} />
      <circle cx={60} cy={40} r={10} />
      <rect x={0} y={18} width={18} height={44} />
      <rect x={102} y={18} width={18} height={44} />
      <rect x={0} y={30} width={6} height={20} />
      <rect x={114} y={30} width={6} height={20} />
      <path d="M18 32 A10 10 0 0 1 18 48" />
      <path d="M102 32 A10 10 0 0 0 102 48" />
      <rect x={-2} y={36} width={2} height={8} />
      <rect x={120} y={36} width={2} height={8} />
      <g fill="var(--pitch-line)" stroke="none">
        <circle cx={60} cy={40} r={0.6} />
        <circle cx={12} cy={40} r={0.6} />
        <circle cx={108} cy={40} r={0.6} />
      </g>
    </g>
  );
}

/**
 * The pitch with mowing stripes. Children are drawn in pitch coordinates. For data layers (heatmaps) pass `dim` to
 * darken the grass so colour reads clearly, and `linesOver` to keep the markings visible on top of the data.
 */
export function PitchSvg({ label, children, className = "", dim = false, linesOver = false }: { label: string; children?: ReactNode; className?: string; dim?: boolean; linesOver?: boolean }) {
  return (
    <svg viewBox="-4 -4 128 88" role="img" aria-label={label} className={`h-auto w-full border-2 border-rule ${className}`}>
      <rect x={-4} y={-4} width={128} height={88} fill="var(--pitch-a)" />
      {Array.from({ length: 6 }, (_, i) => (
        <rect key={i} x={i * 20 + 10} y={-4} width={10} height={88} fill="var(--pitch-b)" />
      ))}
      {dim && <rect x={-4} y={-4} width={128} height={88} fill="#05100a" fillOpacity={0.62} />}
      {!linesOver && <PitchLines />}
      {children}
      {linesOver && <PitchLines />}
    </svg>
  );
}
