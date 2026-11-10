"use client";

import { Badge } from "@/components/ui/Badge";
import { useApi } from "@/lib/api";
import { xgStory } from "@/lib/format";
import type { Match, MatchStats } from "@/lib/types";

const day = (iso: string) => String(new Date(iso + "T00:00:00").getDate());
const month = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { month: "short" });

function Ticket({ match, selected, onSelect }: { match: Match; selected: boolean; onSelect: () => void }) {
  const { data } = useApi<MatchStats>(`/api/v1/matches/${match.id}/stats`);
  const story = xgStory(match, data);
  return (
    <button
      onClick={onSelect}
      aria-current={selected ? "true" : undefined}
      className={`ticket lift grid w-[17.5rem] shrink-0 grid-cols-[60px_1fr] border-2 text-left lg:w-full ${selected ? "border-rule bg-surface shadow-[4px_4px_0_var(--card)]" : "border-line bg-surface/70 hover:border-rule hover:bg-surface"}`}
    >
      <span aria-hidden className="perforation absolute bottom-3 top-3 z-10" style={{ left: 60 }} />
      <span className={`flex flex-col items-center justify-center py-3 font-display uppercase leading-none transition-colors ${selected ? "bg-card text-cardfg" : "bg-surface2 text-fg"}`}>
        <span className="text-[34px] font-extrabold">{day(match.date)}</span>
        <span className="mt-1 text-sm font-semibold tracking-[0.2em]">{month(match.date)}</span>
      </span>
      <span className="min-w-0 py-2.5 pl-4 pr-3">
        <span className="block font-display text-xs font-semibold uppercase tracking-[0.18em] text-muted">{match.stage}</span>
        <span className="mt-1 grid grid-cols-[1fr_auto] items-baseline gap-x-3 gap-y-0.5">
          <span className="truncate font-display text-xl font-bold uppercase leading-tight">{match.home_team.name}</span>
          <span className="tabular font-display text-2xl font-extrabold leading-none">{match.home_score}</span>
          <span className="truncate font-display text-xl font-bold uppercase leading-tight">{match.away_team.name}</span>
          <span className="tabular font-display text-2xl font-extrabold leading-none">{match.away_score}</span>
        </span>
        {data && (
          <span className="tabular mt-1 block text-xs text-muted">
            xG {data.home.xg.toFixed(2)} – {data.away.xg.toFixed(2)}
          </span>
        )}
        {story && (
          <Badge tone="card" className="mt-1.5 !whitespace-normal !text-left !normal-case !tracking-normal !font-sans !text-[11px] !font-semibold leading-snug">
            {story}
          </Badge>
        )}
      </span>
    </button>
  );
}

export function MatchList({ matches, selectedId, onSelect }: { matches: Match[]; selectedId: number | null; onSelect: (id: number) => void }) {
  return (
    <nav aria-label="Matches" className="flex gap-4 overflow-x-auto px-1 pb-4 pt-2 lg:flex-col lg:overflow-visible lg:pb-0">
      {matches.map((m) => (
        <Ticket key={m.id} match={m} selected={m.id === selectedId} onSelect={() => onSelect(m.id)} />
      ))}
    </nav>
  );
}
