"use client";

import { useEffect, useState } from "react";

// An attacking move, left to right. Illustrative, not match data. The ball is driven by one clock so passes, ball,
// xG label and VAR stamp can never drift apart. With reduced motion the board shows its final frame.
const PTS: [number, number][] = [
  [70, 300],
  [170, 190],
  [290, 270],
  [400, 120],
  [480, 205],
  [600, 188],
];
const SHIRTS = [4, 8, 10, 9, 11];
const DEFENDERS: [number, number][] = [
  [350, 205],
  [425, 255],
  [520, 150],
  [535, 232],
];
const START = 0.7;
const SEG = 0.95;
const LOOP = 10;
const SHOT_AT = START + 4 * SEG;
const GOAL_AT = START + 5 * SEG;

const clamp = (x: number) => Math.min(1, Math.max(0, x));
const ease = (p: number) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2);

function ballAt(t: number): [number, number] {
  for (let i = 0; i < PTS.length - 1; i++) {
    const p = clamp((t - START - i * SEG) / SEG);
    if (p < 1 || i === PTS.length - 2) {
      const e = ease(p);
      return [PTS[i][0] + (PTS[i + 1][0] - PTS[i][0]) * e, PTS[i][1] + (PTS[i + 1][1] - PTS[i][1]) * e];
    }
  }
  return PTS[PTS.length - 1];
}

export function HeroBoard() {
  const [t, setT] = useState(7.4);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      setT(((now - t0) / 1000) % LOOP);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const [bx, by] = ballAt(t);
  const holder = Math.max(0, Math.min(4, Math.floor((t - START) / SEG)));
  const ripple = clamp((t - GOAL_AT) / 0.9);
  const xgOpacity = clamp((t - SHOT_AT) / 0.4) * (1 - clamp((t - (LOOP - 0.7)) / 0.5));
  const stampIn = clamp((t - (GOAL_AT + 0.45)) / 0.25);
  const stampOut = clamp((t - (LOOP - 0.6)) / 0.5);
  const stamp = stampIn * (1 - stampOut);

  return (
    <figure>
      <svg viewBox="0 0 600 380" className="h-auto w-full border-2 border-white/35" role="img" aria-label="An illustrated attacking move: five passes, a shot, then a VAR check confirms the goal.">
        {Array.from({ length: 12 }, (_, i) => (
          <rect key={i} x={i * 50} y={0} width={50} height={380} fill={i % 2 ? "rgba(255,255,255,0.045)" : "transparent"} />
        ))}
        <g fill="none" stroke="rgba(241,238,223,0.5)" strokeWidth={2}>
          <rect x={2} y={2} width={596} height={376} />
          <line x1={2} y1={190} x2={2} y2={190} />
          <rect x={440} y={70} width={158} height={240} />
          <rect x={540} y={130} width={58} height={120} />
          <path d="M440 150 A62 62 0 0 0 440 230" />
          <circle cx={2} cy={190} r={64} />
          <rect x={598} y={150} width={14} height={80} stroke="#f1eedf" strokeWidth={3} />
        </g>
        <circle cx={510} cy={190} r={2.5} fill="rgba(241,238,223,0.6)" />

        {DEFENDERS.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={11} fill="#ffa94d" stroke="#0a100d" strokeWidth={2} />
        ))}

        {PTS.slice(0, -1).map(([x0, y0], i) => {
          const [x1, y1] = PTS[i + 1];
          const p = ease(clamp((t - START - i * SEG) / SEG));
          const shot = i === PTS.length - 2;
          return (
            <line
              key={i}
              x1={x0}
              y1={y0}
              x2={x1}
              y2={y1}
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={1 - p}
              stroke={shot ? "#f1eedf" : "#ffd23f"}
              strokeWidth={shot ? 3.5 : 3}
              strokeLinecap="round"
              opacity={p > 0 ? 1 : 0}
            />
          );
        })}

        {PTS.slice(0, -1).map(([x, y], i) => (
          <g key={i}>
            {i === holder && t >= START && t < GOAL_AT && <circle cx={x} cy={y} r={22} fill="none" stroke="#ffd23f" strokeWidth={2} opacity={0.7} />}
            <circle cx={x} cy={y} r={15} fill="#5ea8ff" stroke="#0a100d" strokeWidth={2} />
            <text x={x} y={y + 5} textAnchor="middle" fontSize={15} fontWeight={800} fill="#0a100d" style={{ fontFamily: "var(--font-barlow)" }}>
              {SHIRTS[i]}
            </text>
          </g>
        ))}

        <g opacity={xgOpacity} style={{ fontFamily: "var(--font-barlow)" }}>
          <rect x={448} y={228} width={92} height={26} fill="#0a100d" stroke="#f1eedf" strokeWidth={1.5} />
          <text x={494} y={247} textAnchor="middle" fontSize={17} fontWeight={700} fill="#f1eedf" letterSpacing={1}>
            xG 0.31
          </text>
        </g>

        {ripple > 0 && <circle cx={600} cy={190} r={8 + 70 * ripple} fill="none" stroke="#ffd23f" strokeWidth={3} opacity={1 - ripple} />}
        <circle cx={bx} cy={by} r={8} fill="#f1eedf" stroke="#0a100d" strokeWidth={2.5} />

        <g opacity={stamp} transform={`translate(176 62) rotate(-4) scale(${0.9 + 0.1 * stampIn})`} style={{ fontFamily: "var(--font-barlow)" }}>
          <rect x={0} y={0} width={248} height={54} fill="#0a100d" stroke="#ffd23f" strokeWidth={3} />
          <rect x={5} y={5} width={238} height={44} fill="none" stroke="#ffd23f" strokeWidth={1} />
          <polyline points="18,28 28,39 46,16" fill="none" stroke="#46d685" strokeWidth={5} strokeLinecap="square" />
          <text x={62} y={26} fontSize={13} fontWeight={600} letterSpacing={3} fill="#ffd23f">
            VAR CHECK
          </text>
          <text x={62} y={44} fontSize={20} fontWeight={800} letterSpacing={1} fill="#f1eedf">
            GOAL STANDS
          </text>
        </g>
      </svg>
      <figcaption className="mt-2 font-display text-xs uppercase tracking-[0.2em] text-white/55">Illustrative move: pass, pass, pass, pass, shot, VAR check.</figcaption>
    </figure>
  );
}
