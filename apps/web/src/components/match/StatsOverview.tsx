import { fmt } from "@/lib/format";
import type { MatchStats, TeamStats } from "@/lib/types";

type RowDef = { label: string; get: (t: TeamStats) => number | null; digits?: number; unit?: string; lowerBetter?: boolean; hint?: string };

const ROWS: RowDef[] = [
  { label: "Goals", get: (t) => t.goals, digits: 0 },
  { label: "Expected goals (xG)", get: (t) => t.xg },
  { label: "Non-penalty xG", get: (t) => t.np_xg },
  { label: "Shots", get: (t) => t.shots, digits: 0 },
  { label: "Shots on target", get: (t) => t.shots_on_target, digits: 0 },
  { label: "xG per shot", get: (t) => t.xg_per_shot, digits: 3, hint: "how good the average chance was" },
  { label: "Passes", get: (t) => t.passes, digits: 0 },
  { label: "Pass accuracy", get: (t) => t.pass_accuracy_pct, digits: 1, unit: "%" },
  { label: "Pass share", get: (t) => t.pass_share_pct, digits: 1, unit: "%", hint: "share of all passes, a proxy for possession" },
  { label: "Pressures", get: (t) => t.pressures, digits: 0 },
  { label: "PPDA", get: (t) => t.ppda, digits: 1, lowerBetter: true, hint: "passes allowed per defensive action; lower = harder press" },
  { label: "Fouls committed", get: (t) => t.fouls_committed, digits: 0 },
  { label: "Corners", get: (t) => t.corners, digits: 0 },
];

function Row({ def, home, away, index }: { def: RowDef; home: TeamStats; away: TeamStats; index: number }) {
  const h = def.get(home);
  const a = def.get(away);
  const share = h != null && a != null && h + a > 0 ? (h / (h + a)) * 100 : 50;
  const better = h == null || a == null || h === a ? null : (h > a) !== !!def.lowerBetter ? "home" : "away";
  const show = (v: number | null) => `${fmt(v, def.digits ?? 2)}${v != null && def.unit ? def.unit : ""}`;
  return (
    <div className="group -mx-2 px-2 py-1.5 transition-colors hover:bg-surface2">
      <div className="tabular flex items-baseline justify-between gap-3">
        <span className={`w-24 font-display text-2xl font-bold leading-none ${better === "home" ? "text-home" : "text-fg"}`}>{show(h)}</span>
        <span className="flex-1 text-center">
          <span className="font-display text-sm font-semibold uppercase tracking-[0.14em]">{def.label}</span>
          {def.hint && <span className="block text-[11px] leading-tight text-muted">{def.hint}</span>}
        </span>
        <span className={`w-24 text-right font-display text-2xl font-bold leading-none ${better === "away" ? "text-away" : "text-fg"}`}>{show(a)}</span>
      </div>
      <div className="grow-x mt-1.5 flex h-2 overflow-hidden bg-surface2 group-hover:bg-line" aria-hidden style={{ animationDelay: `${index * 45}ms` }}>
        <div style={{ width: `${share}%`, background: "var(--home)", opacity: better === "away" ? 0.4 : 1 }} />
        <div className="w-px bg-bg" />
        <div className="flex-1" style={{ background: "var(--away)", opacity: better === "home" ? 0.4 : 1 }} />
      </div>
    </div>
  );
}

export function StatsOverview({ stats }: { stats: MatchStats }) {
  const { home, away } = stats;
  return (
    <div>
      <div className="mb-2 flex justify-between border-b-2 border-rule pb-1 font-display text-xl font-bold uppercase tracking-wide">
        <span className="text-home">{home.team}</span>
        <span className="text-away">{away.team}</span>
      </div>
      <div>
        {ROWS.map((r, i) => (
          <Row key={r.label} def={r} home={home} away={away} index={i} />
        ))}
      </div>
      {home.shootout_goals != null && (
        <p className="mt-4 border-2 border-dashed border-line px-3 py-2 text-sm">
          Penalty shootout: {home.team} {home.shootout_goals}–{away.shootout_goals} {away.team}. Shootout kicks are not counted in any number above.
        </p>
      )}
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-display text-base font-semibold uppercase tracking-wide text-muted hover:text-fg">How each number is defined</summary>
        <dl className="mt-2 space-y-1.5 text-muted">
          {Object.entries(stats.definitions).map(([k, v]) => (
            <div key={k}>
              <dt className="inline font-mono text-xs text-fg">{k}</dt> <dd className="inline">{v}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}
