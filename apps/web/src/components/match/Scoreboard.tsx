import { dateLabel, fmt } from "@/lib/format";
import type { Match, MatchStats } from "@/lib/types";

/** The stadium scoreboard. Always dark, like the real thing, in both themes. */
export function Scoreboard({ match, stats }: { match: Match; stats: MatchStats | undefined }) {
  const pens = stats?.home.shootout_goals != null ? `${stats.home.shootout_goals}–${stats.away.shootout_goals} on penalties` : null;
  return (
    <section aria-label="Scoreboard" className="border-2 border-rule bg-[#0a100d] text-[#f1eedf] shadow-[5px_5px_0_var(--rule)]">
      <div className="flex items-center justify-between border-b border-white/15 px-4 py-1.5 font-display text-xs font-semibold uppercase tracking-[0.22em] text-white/60">
        <span>{match.stage}</span>
        <span>{dateLabel(match.date)}</span>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 py-4 sm:gap-6 sm:py-5">
        <div className="min-w-0 text-right">
          <p className="truncate font-display text-2xl font-bold uppercase leading-none sm:text-4xl">{match.home_team.name}</p>
          <span aria-hidden className="mt-2 ml-auto block h-1.5 w-16 bg-home sm:w-24" />
        </div>
        <div key={match.id} className="flex items-center gap-1.5 font-display text-5xl font-extrabold leading-none sm:text-7xl" aria-label={`${match.home_score} – ${match.away_score}`}>
          <span className="anim-pop bg-[#f1eedf] px-2.5 py-1 text-[#0a100d] sm:px-4">{match.home_score}</span>
          <span aria-hidden className="text-white/40">
            –
          </span>
          <span className="anim-pop bg-[#f1eedf] px-2.5 py-1 text-[#0a100d] sm:px-4" style={{ animationDelay: "90ms" }}>
            {match.away_score}
          </span>
        </div>
        <div className="min-w-0">
          <p className="truncate font-display text-2xl font-bold uppercase leading-none sm:text-4xl">{match.away_team.name}</p>
          <span aria-hidden className="mt-2 block h-1.5 w-16 bg-away sm:w-24" />
        </div>
      </div>
      {stats && (
        <div className="tabular flex flex-wrap items-center justify-center gap-x-6 gap-y-1 border-t border-white/15 px-4 py-1.5 font-display text-sm font-semibold uppercase tracking-[0.18em] text-white/70">
          <span>
            xG {fmt(stats.home.xg)} – {fmt(stats.away.xg)}
          </span>
          <span>
            Shots {stats.home.shots} – {stats.away.shots}
          </span>
          {pens && <span className="text-card">{pens}</span>}
        </div>
      )}
    </section>
  );
}
