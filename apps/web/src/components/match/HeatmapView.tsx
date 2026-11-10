"use client";

import { useState } from "react";
import { useApi } from "@/lib/api";
import { HEAT_LEGEND, heatColor } from "@/lib/heat";
import type { Heatmap, Match, PlayerStats } from "@/lib/types";
import { PitchSvg } from "./Pitch";

const KINDS = [
  ["actions", "On-ball actions"],
  ["passes", "Passes"],
  ["pressures", "Pressures"],
  ["shots", "Shots"],
] as const;

const select = "border-2 border-rule bg-surface px-2 py-1.5 text-sm hover:bg-surface2";
const label = "flex flex-col gap-1 font-display text-sm font-semibold uppercase tracking-[0.14em]";

export function HeatmapView({ match, players, initialPlayerId }: { match: Match; players: PlayerStats[]; initialPlayerId: number | null }) {
  const initial = players.find((p) => p.player_id === initialPlayerId);
  const [teamId, setTeamId] = useState<number>(initial ? (initial.team === match.home_team.name ? match.home_team.id : match.away_team.id) : match.home_team.id);
  const [playerId, setPlayerId] = useState<number | null>(initialPlayerId);
  const [kind, setKind] = useState<(typeof KINDS)[number][0]>("actions");
  const [hover, setHover] = useState<{ r: number; c: number } | null>(null);

  const teamName = teamId === match.home_team.id ? match.home_team.name : match.away_team.name;
  const squad = players.filter((p) => p.team === teamName && p.minutes > 0).sort((a, b) => b.minutes - a.minutes);
  const path = `/api/v1/matches/${match.id}/heatmap?${playerId ? `player_id=${playerId}` : `team_id=${teamId}`}&kind=${kind}`;
  const { data, error, loading } = useApi<Heatmap>(path);

  const cell = data ? data.cell_yards : 10;
  const readout = hover && data ? `${data.cells[hover.r][hover.c]} events · ${hover.c * cell}–${(hover.c + 1) * cell} yards upfield, ${hover.r * cell}–${(hover.r + 1) * cell} across` : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4">
        <label className={label}>
          Team
          <select
            value={teamId}
            onChange={(e) => {
              setTeamId(Number(e.target.value));
              setPlayerId(null);
            }}
            className={select}
          >
            <option value={match.home_team.id}>{match.home_team.name}</option>
            <option value={match.away_team.id}>{match.away_team.name}</option>
          </select>
        </label>
        <label className={label}>
          Player
          <select value={playerId ?? ""} onChange={(e) => setPlayerId(e.target.value ? Number(e.target.value) : null)} className={`${select} max-w-56`}>
            <option value="">Whole team</option>
            {squad.map((p) => (
              <option key={p.player_id} value={p.player_id}>
                {p.display_name} ({Math.round(p.minutes)}′)
              </option>
            ))}
          </select>
        </label>
        <label className={label}>
          Show
          <select value={kind} onChange={(e) => setKind(e.target.value as typeof kind)} className={select}>
            {KINDS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <p className="tabular font-display text-xl font-bold uppercase tracking-wide" aria-live="polite">
          {loading ? "Warming up…" : data ? `${data.total} events` : ""}
        </p>
      </div>
      {error && <p className="border-2 border-red/50 px-3 py-2 text-sm text-red">Own goal: could not load the heatmap. {error}</p>}

      <PitchSvg dim linesOver label={`Heatmap of ${kind} for ${playerId ? squad.find((p) => p.player_id === playerId)?.display_name : teamName}. Redder squares have more events.`}>
        {data?.cells.map((row, r) =>
          row.map((v, c) => {
            const { fill, opacity } = heatColor(v, data.max);
            const on = hover?.r === r && hover?.c === c;
            return (
              <rect
                key={`${r}-${c}-${data.total}`}
                data-testid={v > 0 ? "heat-cell" : undefined}
                data-count={v}
                x={c * cell}
                y={r * cell}
                width={cell}
                height={cell}
                fill={v > 0 ? fill : "transparent"}
                fillOpacity={v > 0 ? opacity : 0}
                stroke={on ? "var(--fg)" : "none"}
                strokeWidth={0.7}
                className="anim-fade cursor-crosshair"
                style={{ animationDelay: `${c * 28}ms` }}
                onMouseEnter={() => setHover({ r, c })}
                onMouseLeave={() => setHover(null)}
              />
            );
          }),
        )}
        <text x={2} y={-1.2} fontSize={3.2} fill="var(--pitch-line)" style={{ fontFamily: "var(--font-barlow)", letterSpacing: "0.2em" }}>
          ATTACKING →
        </text>
      </PitchSvg>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="min-h-5 text-sm text-muted" aria-live="polite">
          {readout ?? "Hover a square to count its events."}
        </p>
        <div className="flex items-center gap-2 font-display text-xs font-semibold uppercase tracking-[0.18em] text-muted" aria-hidden>
          Cold
          <span className="block h-3 w-40 border border-rule" style={{ background: `${HEAT_LEGEND}, var(--pitch-a)` }} />
          Hot
        </div>
      </div>
      <p className="text-xs text-muted">Events per 10-yard square, periods 1–4 (penalty shootout excluded). Every team is drawn attacking left to right.</p>
    </div>
  );
}
