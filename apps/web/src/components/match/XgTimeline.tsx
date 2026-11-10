"use client";

import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt } from "@/lib/format";
import type { Match, Shot } from "@/lib/types";

/** Cumulative xG for both teams across the match; dots mark goals. */
export function XgTimeline({ match, shots }: { match: Match; shots: Shot[] }) {
  const ordered = [...shots].filter((s) => !s.is_shootout).sort((a, b) => a.period - b.period || a.minute - b.minute || a.second - b.second);
  let home = 0;
  let away = 0;
  const rows = [{ minute: 0, home: 0, away: 0 }];
  const goals: { minute: number; y: number; home: boolean }[] = [];
  for (const s of ordered) {
    const isHome = s.team_id === match.home_team.id;
    if (isHome) home += s.xg ?? 0;
    else away += s.xg ?? 0;
    const minute = s.minute + s.second / 60;
    rows.push({ minute, home, away });
    if (s.outcome === "Goal") goals.push({ minute, y: isHome ? home : away, home: isHome });
  }
  const end = Math.max(90, Math.ceil(Math.max(...rows.map((r) => r.minute))));
  rows.push({ minute: end, home, away });

  return (
    <figure>
      <figcaption className="mb-2 flex items-baseline justify-between border-b-2 border-rule pb-1 font-display text-xl font-bold uppercase tracking-wide">
        <span>Race to xG</span>
        <span className="tabular text-sm font-semibold tracking-[0.14em] text-muted">
          <span className="text-home">{fmt(home)}</span> – <span className="text-away">{fmt(away)}</span>
        </span>
      </figcaption>
      <div className="h-64 w-full" role="img" aria-label={`Cumulative xG: ${match.home_team.name} ${fmt(home)}, ${match.away_team.name} ${fmt(away)}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 10, right: 16, bottom: 0, left: -10 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis dataKey="minute" type="number" domain={[0, end]} tickCount={7} tick={{ fill: "var(--muted)", fontSize: 12 }} stroke="var(--rule)" unit="′" />
            <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} stroke="var(--rule)" width={44} />
            <Tooltip
              contentStyle={{ background: "var(--surface)", border: "2px solid var(--rule)", borderRadius: 0, color: "var(--fg)" }}
              labelFormatter={(m) => `${Math.floor(Number(m))}′`}
              formatter={(v, name) => [fmt(Number(v)), String(name)]}
            />
            <Line name={match.home_team.name} dataKey="home" type="stepAfter" stroke="var(--home)" strokeWidth={3} dot={false} isAnimationActive animationDuration={900} />
            <Line name={match.away_team.name} dataKey="away" type="stepAfter" stroke="var(--away)" strokeWidth={3} dot={false} isAnimationActive animationDuration={900} />
            {goals.map((g, i) => (
              <ReferenceDot key={i} x={g.minute} y={g.y} r={6} fill={g.home ? "var(--home)" : "var(--away)"} stroke="var(--fg)" strokeWidth={2} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs text-muted">Cumulative expected goals by minute (penalty shootout excluded). Dots are goals.</p>
    </figure>
  );
}
