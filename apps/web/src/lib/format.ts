import type { Match, MatchStats } from "./types";

export const fmt = (n: number | null | undefined, digits = 2) => (n == null ? "–" : n.toFixed(digits));

export const shortId = (id: string) => id.slice(0, 8);

export const dateLabel = (iso: string) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

/** One-line story hook: the side with more xG did not win. */
export function xgStory(match: Match, stats: MatchStats | undefined): string | null {
  if (!stats) return null;
  const { home, away } = stats;
  if (home.xg === away.xg) return null;
  const leader = home.xg > away.xg ? home : away;
  const other = leader === home ? away : home;
  if (leader.goals > other.goals) return null;
  const xg = `${leader.team} had more xG (${fmt(leader.xg)} v ${fmt(other.xg)})`;
  if (leader.goals < other.goals) return `${xg} but lost`;
  return stats.home.shootout_goals != null ? `${xg}; level after extra time, decided on penalties` : `${xg} but could not break through`;
}
