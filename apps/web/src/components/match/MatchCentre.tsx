"use client";

import { useState, type ReactNode } from "react";
import { SectionTitle } from "@/components/ui/Badge";
import { Tabs, type TabDef } from "@/components/ui/Tabs";
import { useApi } from "@/lib/api";
import { setHash, useHash } from "@/lib/hash";
import type { Match, MatchStats, PlayerStats, Shot } from "@/lib/types";
import { Analyst } from "./Analyst";
import { HeatmapView } from "./HeatmapView";
import { MatchList } from "./MatchList";
import { PlayersTable } from "./PlayersTable";
import { Scoreboard } from "./Scoreboard";
import { ShotMap } from "./ShotMap";
import { StatsOverview } from "./StatsOverview";
import { XgTimeline } from "./XgTimeline";

type TabId = "overview" | "shots" | "players" | "heatmaps" | "analyst";
const TABS: TabDef<TabId>[] = [
  { id: "overview", label: "Full Time", hint: "the stats" },
  { id: "shots", label: "Shot Map", hint: "xG and 360 context" },
  { id: "players", label: "Squad Sheet", hint: "minutes and output" },
  { id: "heatmaps", label: "Heat Check", hint: "where it happened" },
  { id: "analyst", label: "Analyst", hint: "the VAR room" },
];

const Note = ({ children, bad }: { children: ReactNode; bad?: boolean }) => (
  <p className={`border-2 border-dashed px-4 py-3 text-sm ${bad ? "border-red/60 text-red" : "border-line text-muted"}`} role={bad ? "alert" : "status"}>
    {children}
  </p>
);

export function MatchCentre() {
  const hash = useHash();
  const params = new URLSearchParams(hash);
  const matches = useApi<Match[]>("/api/v1/matches");
  const matchId = Number(params.get("match")) || matches.data?.[0]?.id || null;
  const tab = (TABS.some((t) => t.id === params.get("tab")) ? params.get("tab") : "overview") as TabId;
  const match = matches.data?.find((m) => m.id === matchId) ?? null;

  const stats = useApi<MatchStats>(match ? `/api/v1/matches/${match.id}/stats` : null);
  const shots = useApi<Shot[]>(match ? `/api/v1/matches/${match.id}/shots` : null);
  const players = useApi<PlayerStats[]>(match ? `/api/v1/matches/${match.id}/players` : null);

  const [highlight, setHighlight] = useState<string | null>(null);
  const [heatPlayer, setHeatPlayer] = useState<number | null>(null);

  const showEvidence = (id: string) => {
    if (shots.data?.some((s) => s.event_id === id)) {
      setHighlight(id);
      setHash({ tab: "shots" });
    } else {
      navigator.clipboard?.writeText(id).catch(() => {});
    }
  };

  return (
    <section id="match-centre" aria-label="Match Centre" className="mx-auto w-full max-w-7xl scroll-mt-20 px-4 pt-14">
      <SectionTitle kicker="Match Centre" title="Pick a fixture">
        Five matches from the 2022 World Cup. The ticket badge marks games where the side with more expected goals didn&apos;t win.
      </SectionTitle>

      {matches.loading && (
        <Note>
          Warming up… The API runs on a free hosting plan that sleeps when idle, so the first load can take up to a minute. Nothing is broken: please be patient.
        </Note>
      )}
      {matches.error && (
        <Note bad>
          Own goal: could not reach the API. {matches.error} If the server was asleep (free hosting plan), wait a minute and reload. Running locally? Start it
          (<code>uvicorn app.main:app</code> in apps/api).
        </Note>
      )}

      {matches.data && match && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]">
          <aside>
            <MatchList
              matches={matches.data}
              selectedId={match.id}
              onSelect={(id) => {
                setHighlight(null);
                setHash({ match: id });
              }}
            />
          </aside>

          <div aria-label="Match analysis" className="min-w-0 space-y-6">
            <Scoreboard match={match} stats={stats.data} />
            <Tabs tabs={TABS} value={tab} onChange={(id) => setHash({ tab: id })} label="Views" />

            <div role="tabpanel" className="pb-6">
              {tab === "overview" &&
                (stats.error ? <Note bad>{stats.error}</Note> : stats.data && shots.data ? (
                  <div className="grid gap-10 xl:grid-cols-2">
                    <StatsOverview stats={stats.data} />
                    <XgTimeline match={match} shots={shots.data} />
                  </div>
                ) : <Note>Lining up the wall…</Note>)}
              {tab === "shots" &&
                (shots.error ? <Note bad>{shots.error}</Note> : shots.data ? (
                  <ShotMap key={`${match.id}-${highlight}`} match={match} shots={shots.data} highlight={highlight} />
                ) : <Note>Lining up the wall…</Note>)}
              {tab === "players" &&
                (players.error ? <Note bad>{players.error}</Note> : players.data ? (
                  <PlayersTable
                    match={match}
                    players={players.data}
                    onHeatmap={(p) => {
                      setHeatPlayer(p.player_id);
                      setHash({ tab: "heatmaps" });
                    }}
                  />
                ) : <Note>Reading the team sheet…</Note>)}
              {tab === "heatmaps" &&
                (players.error ? <Note bad>{players.error}</Note> : players.data ? (
                  <HeatmapView key={`${match.id}-${heatPlayer}`} match={match} players={players.data} initialPlayerId={heatPlayer} />
                ) : <Note>Reading the team sheet…</Note>)}
              {tab === "analyst" && <Analyst key={match.id} match={match} stats={stats.data} onShowEvidence={showEvidence} />}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
