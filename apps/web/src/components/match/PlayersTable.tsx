"use client";

import { useState } from "react";
import { fmt } from "@/lib/format";
import type { Match, PlayerStats } from "@/lib/types";

type Key = keyof PlayerStats;
const COLS: { key: Key; label: string; title: string; digits?: number }[] = [
  { key: "minutes", label: "Min", title: "Minutes played (periods 1-4)", digits: 0 },
  { key: "shots", label: "Sh", title: "Shots", digits: 0 },
  { key: "goals", label: "G", title: "Goals", digits: 0 },
  { key: "xg", label: "xG", title: "Expected goals" },
  { key: "np_xg", label: "npxG", title: "Non-penalty expected goals" },
  { key: "key_passes", label: "KP", title: "Key passes (passes leading to a shot)", digits: 0 },
  { key: "assists", label: "A", title: "Assists", digits: 0 },
  { key: "passes", label: "Pass", title: "Passes attempted", digits: 0 },
  { key: "pressures", label: "Press", title: "Pressures", digits: 0 },
  { key: "tackles", label: "Tkl", title: "Tackles", digits: 0 },
  { key: "interceptions", label: "Int", title: "Interceptions", digits: 0 },
];

export function PlayersTable({ match, players, onHeatmap }: { match: Match; players: PlayerStats[]; onHeatmap: (p: PlayerStats) => void }) {
  const [sort, setSort] = useState<Key>("xg");
  const [team, setTeam] = useState<string>("all");
  const rows = players
    .filter((p) => p.minutes > 0 && (team === "all" || p.team === team))
    .sort((a, b) => (b[sort] as number) - (a[sort] as number) || b.minutes - a.minutes);
  const maxXg = Math.max(0.01, ...rows.map((p) => p.xg));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2 font-display text-base font-semibold uppercase tracking-wide">
          Team
          <select value={team} onChange={(e) => setTeam(e.target.value)} className="border-2 border-rule bg-surface px-2 py-1 font-sans text-sm normal-case tracking-normal hover:bg-surface2">
            <option value="all">Both</option>
            <option value={match.home_team.name}>{match.home_team.name}</option>
            <option value={match.away_team.name}>{match.away_team.name}</option>
          </select>
        </label>
        <span className="text-muted">Sorted by {COLS.find((c) => c.key === sort)?.label}. Select a column header to re-sort.</span>
      </div>
      <div className="overflow-x-auto border-2 border-rule bg-surface">
        <table className="tabular w-full min-w-[720px] text-sm">
          <thead className="bg-rule text-left text-[#f1eedf]">
            <tr>
              <th className="px-3 py-2 font-display text-sm font-semibold uppercase tracking-[0.14em]">Player</th>
              {COLS.map((c) => (
                <th key={c.key} className="px-2 py-2 text-right" title={c.title}>
                  <button
                    onClick={() => setSort(c.key)}
                    aria-label={`Sort by ${c.title}`}
                    className={`font-display text-sm font-semibold uppercase tracking-[0.14em] transition-colors hover:text-card ${sort === c.key ? "text-card" : ""}`}
                  >
                    {c.label}
                    {sort === c.key && <span aria-hidden> ▾</span>}
                  </button>
                </th>
              ))}
              <th className="px-2 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((p) => (
              <tr key={p.player_id} className="group transition-colors hover:bg-surface2">
                <td className="px-3 py-1.5 font-medium">
                  <i className={`mr-2 inline-block h-2.5 w-2.5 rounded-full ${p.team === match.home_team.name ? "bg-home" : "bg-away"}`} />
                  {p.display_name}
                  {!p.started && <span className="ml-1 text-xs font-normal text-muted">(sub)</span>}
                </td>
                {COLS.map((c) => (
                  <td key={c.key} className={`relative px-2 py-1.5 text-right ${c.key === sort ? "font-bold" : ""}`}>
                    {c.key === "xg" && <span aria-hidden className="absolute inset-y-1.5 right-0 bg-card/45" style={{ width: `${(p.xg / maxXg) * 100}%`, maxWidth: "100%" }} />}
                    <span className="relative">{fmt(p[c.key] as number, c.digits ?? 2)}</span>
                  </td>
                ))}
                <td className="px-2 py-1.5 text-right">
                  <button
                    onClick={() => onHeatmap(p)}
                    className="border-2 border-line px-2 py-0.5 font-display text-xs font-semibold uppercase tracking-wider transition-colors hover:border-rule hover:bg-card hover:text-cardfg"
                  >
                    Heatmap
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
