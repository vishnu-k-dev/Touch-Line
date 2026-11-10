"use client";

import { useState } from "react";
import { fmt, shortId } from "@/lib/format";
import type { Match, Shot } from "@/lib/types";
import { PitchSvg } from "./Pitch";

const radius = (xg: number | null) => 0.9 + 4.2 * Math.sqrt(xg ?? 0);

function laneNote(s: Shot) {
  if (s.cone_visible && s.defenders_in_cone != null) {
    const n = s.defenders_in_cone;
    return `${n === 0 ? "No" : n} visible defender${n === 1 ? "" : "s"} in the shooting lane (a lower bound)`;
  }
  return s.cone_visible === false ? "Shooting lane only partly in the 360 camera view" : "No 360 freeze-frame for this shot";
}

export function ShotMap({ match, shots, highlight }: { match: Match; shots: Shot[]; highlight: string | null }) {
  const [goalsOnly, setGoalsOnly] = useState(false);
  const [noPens, setNoPens] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(highlight);

  const visible = shots.filter((s) => s.x != null && s.y != null && (!goalsOnly || s.outcome === "Goal") && (!noPens || s.shot_type !== "Penalty"));
  const active = shots.find((s) => s.event_id === (hover ?? pinned ?? highlight)) ?? null;
  const top = [...visible].sort((a, b) => (b.xg ?? 0) - (a.xg ?? 0)).slice(0, 8);
  const isHome = (s: Shot) => s.team_id === match.home_team.id;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
        <span className="flex items-center gap-2 font-display text-lg font-semibold uppercase tracking-wide">
          <i className="inline-block h-3.5 w-3.5 rounded-full bg-home" /> {match.home_team.name} <span className="font-sans text-xs font-normal normal-case text-muted">attacks right</span>
        </span>
        <span className="flex items-center gap-2 font-display text-lg font-semibold uppercase tracking-wide">
          <i className="inline-block h-3.5 w-3.5 rounded-full bg-away" /> {match.away_team.name} <span className="font-sans text-xs font-normal normal-case text-muted">attacks left</span>
        </span>
        <label className="ml-auto flex cursor-pointer items-center gap-2">
          <input type="checkbox" className="accent-[var(--card)]" checked={goalsOnly} onChange={(e) => setGoalsOnly(e.target.checked)} /> Goals only
        </label>
        <label className="flex cursor-pointer items-center gap-2">
          <input type="checkbox" className="accent-[var(--card)]" checked={noPens} onChange={(e) => setNoPens(e.target.checked)} /> Hide penalties
        </label>
      </div>

      <PitchSvg label={`Shot map: ${visible.length} shots. Dot size is expected goals; filled dots are goals.`}>
        {visible.map((s, i) => {
          const home = isHome(s);
          const x = home ? s.x! : 120 - s.x!;
          const y = home ? s.y! : 80 - s.y!;
          const goal = s.outcome === "Goal";
          const on = active?.event_id === s.event_id;
          const color = home ? "var(--home)" : "var(--away)";
          const r = radius(s.xg);
          return (
            <g
              key={s.event_id}
              tabIndex={0}
              role="button"
              aria-label={`${s.display_name}, ${s.minute} minutes, ${fmt(s.xg)} expected goals, ${s.outcome}`}
              onMouseEnter={() => setHover(s.event_id)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(s.event_id)}
              onBlur={() => setHover(null)}
              onClick={() => setPinned(s.event_id)}
              className="anim-fade cursor-pointer outline-none"
              style={{ animationDelay: `${Math.min(i * 14, 500)}ms` }}
            >
              <g className="transition-transform duration-150 ease-out hover:scale-[1.35] focus-visible:scale-[1.35]" style={{ transformBox: "fill-box", transformOrigin: "center", transform: on ? "scale(1.35)" : undefined }}>
                {on && <circle cx={x} cy={y} r={r + 1} fill="none" stroke="var(--card)" strokeWidth={0.7} style={{ transformBox: "fill-box", transformOrigin: "center", animation: "ring 1.2s ease-out infinite" }} />}
                <circle cx={x} cy={y} r={r} fill={color} fillOpacity={goal ? 0.95 : 0.34} stroke={on ? "var(--card)" : color} strokeWidth={on ? 1 : goal ? 0.7 : 0.45} />
                {goal && <circle cx={x} cy={y} r={r + 1.5} fill="none" stroke={color} strokeWidth={0.4} />}
              </g>
            </g>
          );
        })}
      </PitchSvg>
      <p className="text-xs text-muted">Dot area is expected goals (xG). Filled, ringed dots are goals. Penalty-shootout kicks are excluded. Select a dot for details.</p>

      <div className="min-h-[7.5rem] border-2 border-rule bg-surface p-4 text-sm" aria-live="polite">
        {active ? (
          <dl key={active.event_id} className="anim-slide-up grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
            <div className="col-span-2 sm:col-span-4">
              <dt className="sr-only">Shot</dt>
              <dd className="font-display text-2xl font-bold uppercase leading-none">
                {active.display_name} <span className="font-sans text-sm font-normal normal-case text-muted">({active.team}) · {active.minute}&prime;</span>
              </dd>
            </div>
            <div><dt className="text-xs uppercase tracking-wider text-muted">xG</dt><dd className="tabular font-display text-xl font-bold">{fmt(active.xg, 3)}</dd></div>
            <div><dt className="text-xs uppercase tracking-wider text-muted">Outcome</dt><dd className="font-display text-xl font-bold uppercase">{active.outcome}</dd></div>
            <div><dt className="text-xs uppercase tracking-wider text-muted">Type</dt><dd>{active.shot_type ?? "–"} · {active.body_part ?? "–"}</dd></div>
            <div><dt className="text-xs uppercase tracking-wider text-muted">Event id</dt><dd className="font-mono text-xs" title={active.event_id}>{shortId(active.event_id)}…</dd></div>
            <div className="col-span-2 text-muted sm:col-span-4">360 freeze-frame: {laneNote(active)}</div>
          </dl>
        ) : (
          <p className="text-muted">Hover, focus or click a shot to see who took it, its xG, and the 360 freeze-frame context.</p>
        )}
      </div>

      <div>
        <h3 className="mb-2 border-b-2 border-rule pb-1 font-display text-xl font-bold uppercase tracking-wide">Best chances</h3>
        <ul className="divide-y divide-line border-2 border-line bg-surface text-sm">
          {top.map((s) => (
            <li key={s.event_id}>
              <button
                onClick={() => setPinned(s.event_id)}
                className={`flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-surface2 ${active?.event_id === s.event_id ? "bg-surface2" : ""}`}
              >
                <i className={`h-2.5 w-2.5 rounded-full ${isHome(s) ? "bg-home" : "bg-away"}`} />
                <span className="tabular w-10 text-muted">{s.minute}&prime;</span>
                <span className="flex-1 truncate font-medium">{s.display_name}</span>
                <span className="text-muted">{s.outcome}</span>
                <span className="tabular w-12 text-right font-display text-lg font-bold">{fmt(s.xg)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
