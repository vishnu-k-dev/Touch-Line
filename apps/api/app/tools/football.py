"""The analyst's tools. Each tool validates its arguments (pydantic), reads only from the database, returns bounded
JSON, and raises ToolError with a message the model can act on (the agent loop feeds that message back to it)."""

import unicodedata
from dataclasses import dataclass
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tables import Event, Match, Player
from app.services import analytics, rag


class ToolError(Exception):
    pass


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListMatchesArgs(_Args):
    team: str | None = Field(None, description="Only matches involving this team (name or part of it).")


class MatchArgs(_Args):
    match_id: int = Field(description="Match id from list_matches.")


class ShotMapArgs(MatchArgs):
    team: str | None = Field(None, description="Only this team's shots.")
    player: str | None = Field(None, description="Only this player's shots (name or part of it).")
    outcome: str | None = Field(None, description="Goal, Saved, Blocked, Off T, Post, Wayward or Saved Off Target.")
    include_shootout: bool = Field(False, description="Include penalty-shootout kicks (excluded from all match stats).")
    limit: int = Field(30, ge=1, le=60)


class PlayerStatsArgs(MatchArgs):
    player: str | None = Field(None, description="Name or part of it.")
    team: str | None = None
    limit: int = Field(10, ge=1, le=30)


class ComparePlayersArgs(MatchArgs):
    player_a: str
    player_b: str


class TeamEventsArgs(MatchArgs):
    team: str
    event_type: str | None = Field(None, description="e.g. Pass, Pressure, Shot, Foul Committed. Omit for counts of every type.")
    limit: int = Field(15, ge=1, le=40)


class KnowledgeArgs(_Args):
    query: str = Field(min_length=2, max_length=300, description="What to look up, in plain language.")
    kind: Literal["knowledge", "match", "sequence"] | None = Field(
        None, description="knowledge = tactical concepts; match = match summaries; sequence = individual shots and how they were created."
    )
    match_id: int | None = None
    k: int = Field(4, ge=1, le=8)
    team: str | None = Field(None, description="Exact team name filter (sequences only).")
    player: str | None = Field(None, description="Player name filter, substring (sequences only).")
    outcome: str | None = Field(None, description="Exact shot outcome filter (sequences only).")
    shot_type: str | None = Field(None, description="Open Play, Penalty or Free Kick (sequences only).")
    body_part: str | None = Field(None, description="Head, Right Foot or Left Foot (sequences only).")
    play_pattern: str | None = Field(None, description="Regular Play, From Counter, From Corner, From Free Kick, From Throw In ... (sequences only).")


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).casefold()


def _match(db: Session, match_id: int) -> Match:
    m = db.get(Match, match_id)
    if m is None:
        raise ToolError(f"No match with id {match_id}. Call list_matches to see valid ids.")
    return m


def _team(m: Match, name: str):
    hits = [t for t in (m.home_team, m.away_team) if _norm(name) in _norm(t.name)]
    if len(hits) != 1:
        raise ToolError(f"Team {name!r} is not (uniquely) in this match; teams are {m.home_team.name} and {m.away_team.name}.")
    return hits[0]


def _player_rows(db: Session, match_id: int, name: str) -> list[dict]:
    return [p for p in analytics.player_stats(db, match_id) if _norm(name) in _norm(p["player"])]


def _one_player(db: Session, match_id: int, name: str) -> dict:
    rows = _player_rows(db, match_id, name)
    if not rows:
        raise ToolError(f"No player matching {name!r} with recorded actions in this match.")
    if len(rows) > 1:
        raise ToolError(f"{name!r} matches several players: {[r['player'] for r in rows][:6]}. Use a longer name.")
    return rows[0]


def list_matches(db: Session, a: ListMatchesArgs) -> dict:
    q = select(Match).order_by(Match.match_date, Match.id)
    out = [
        {"match_id": m.id, "date": str(m.match_date), "stage": m.stage, "home": m.home_team.name, "away": m.away_team.name,
         "home_score": m.home_score, "away_score": m.away_score}
        for m in db.scalars(q)
        if a.team is None or _norm(a.team) in _norm(m.home_team.name) or _norm(a.team) in _norm(m.away_team.name)
    ]
    return {"matches": out}


def get_match_summary(db: Session, a: MatchArgs) -> dict:
    _match(db, a.match_id)
    return analytics.match_stats(db, a.match_id)


def get_shot_map(db: Session, a: ShotMapArgs) -> dict:
    m = _match(db, a.match_id)
    shots = analytics.shot_map(db, a.match_id, a.include_shootout)
    if a.team:
        shots = [s for s in shots if s["team_id"] == _team(m, a.team).id]
    if a.player:
        shots = [s for s in shots if _norm(a.player) in _norm(s["player"])]
    if a.outcome:
        shots = [s for s in shots if s["outcome"].casefold() == a.outcome.casefold()]
    keep = ("event_id", "team", "player", "minute", "xg", "outcome", "shot_type", "body_part", "x", "y",
            "defenders_in_cone", "cone_visible", "nearest_defender")
    return {
        "match_id": a.match_id, "total_matching": len(shots), "truncated": len(shots) > a.limit,
        "shots": [{k: (round(s[k], 3) if k == "xg" and s[k] is not None else s[k]) for k in keep} for s in shots[: a.limit]],
        "note": "defenders_in_cone counts VISIBLE defenders in the shooting lane from the 360 freeze-frame: a lower bound, "
                "only meaningful when cone_visible is true; null means no freeze-frame.",
    }


def get_player_stats(db: Session, a: PlayerStatsArgs) -> dict:
    m = _match(db, a.match_id)
    rows = analytics.player_stats(db, a.match_id)
    if a.team:
        rows = [r for r in rows if r["team"] == _team(m, a.team).name]
    if a.player:
        rows = [r for r in rows if _norm(a.player) in _norm(r["player"])]
    return {"match_id": a.match_id, "total_matching": len(rows), "players": rows[: a.limit]}


def compare_players(db: Session, a: ComparePlayersArgs) -> dict:
    _match(db, a.match_id)
    pa, pb = _one_player(db, a.match_id, a.player_a), _one_player(db, a.match_id, a.player_b)
    if pa["player_id"] == pb["player_id"]:
        raise ToolError("player_a and player_b are the same player.")
    return {"match_id": a.match_id, "player_a": pa, "player_b": pb}


def get_team_events(db: Session, a: TeamEventsArgs) -> dict:
    m = _match(db, a.match_id)
    team = _team(m, a.team)
    base = (Event.match_id == a.match_id, Event.team_id == team.id)
    counts = dict(db.execute(select(Event.type, func.count()).where(*base).group_by(Event.type)).all())
    if a.event_type is None:
        return {"match_id": a.match_id, "team": team.name, "event_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1]))}
    etype = next((t for t in counts if t.casefold() == a.event_type.casefold()), None)
    if etype is None:
        raise ToolError(f"No {a.event_type!r} events for {team.name}. Available types: {sorted(counts)}")
    rows = db.execute(
        select(Event.id, Event.minute, Event.second, Event.period, Player.name, Event.x, Event.y)
        .join(Player, Player.id == Event.player_id, isouter=True)
        .where(*base, Event.type == etype).order_by(Event.idx).limit(a.limit)
    ).all()
    return {
        "match_id": a.match_id, "team": team.name, "event_type": etype, "total": counts[etype], "returned": len(rows),
        "events": [{"event_id": i, "minute": mi, "second": se, "period": pe, "player": pl, "x": x, "y": y}
                   for i, mi, se, pe, pl, x, y in rows],
    }


def calculate_ppda(db: Session, a: MatchArgs) -> dict:
    _match(db, a.match_id)
    s = analytics.match_stats(db, a.match_id)
    return {
        "match_id": a.match_id,
        "teams": [
            {k: s[side][k] for k in ("team", "ppda", "ppda_passes_allowed", "ppda_defensive_actions", "pressures")}
            for side in ("home", "away")
        ],
        "definition": analytics.DEFINITIONS["ppda"],
    }


def search_tactical_knowledge(db: Session, a: KnowledgeArgs) -> dict:
    filters = {k: v for k, v in dict(team=a.team, player=a.player, outcome=a.outcome, shot_type=a.shot_type,
                                     body_part=a.body_part, play_pattern=a.play_pattern).items() if v}
    if filters and a.kind not in (None, "sequence"):
        raise ToolError("Shot filters only apply to kind='sequence'.")
    hits = rag.search(db, a.query, a.k, "sequence" if filters and a.kind is None else a.kind, a.match_id, filters)
    return {
        "results": [
            {"title": h["title"], "kind": h["kind"], "score": h["score"], "content": h["content"], "match_id": h["match_id"],
             **({"event_ids": h["meta"]["event_ids"]} if h["kind"] == "sequence" else {})}
            for h in hits
        ]
    }


@dataclass
class Tool:
    name: str
    description: str
    args: type[BaseModel]
    fn: Callable[[Session, BaseModel], dict]


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("list_matches", "List the matches in the database (id, date, stage, teams, score). Use first to find a match id.", ListMatchesArgs, list_matches),
    Tool("get_match_summary", "Team-level stats for one match: goals, shots, shots on target, xG, non-penalty xG, passing, pass share, pressures, PPDA, shootout result. Includes metric definitions.", MatchArgs, get_match_summary),
    Tool("get_shot_map", "Every shot in a match (or filtered by team, player or outcome) with xG, outcome, location and event_id evidence. Includes 360 freeze-frame context where available.", ShotMapArgs, get_shot_map),
    Tool("get_player_stats", "Per-player stats for one match: shots, goals, xG, passes, key passes, assists, pressures, tackles, interceptions, minutes played. Sorted by xG.", PlayerStatsArgs, get_player_stats),
    Tool("compare_players", "Side-by-side stats for two players in the same match.", ComparePlayersArgs, compare_players),
    Tool("get_team_events", "A team's event counts by type for a match, or the events of one type (with minute, player, event_id).", TeamEventsArgs, get_team_events),
    Tool("calculate_ppda", "PPDA (passes allowed per defensive action; lower = more intense press) for both teams in a match, with the underlying counts and the definition.", MatchArgs, calculate_ppda),
    Tool("search_tactical_knowledge", "Semantic search over tactical concepts (kind=knowledge), match summaries (kind=match) and individual shot sequences (kind=sequence, with exact filters such as play_pattern, body_part, player). Use for definitions and caveats, or to find specific moments.", KnowledgeArgs, search_tactical_knowledge),
]}


def collect(obj, events: set[str] | None = None, numbers: list[float] | None = None):
    """Walk a tool result, gathering event ids (evidence) and numbers (for checking claims). List lengths count as numbers."""
    events = set() if events is None else events
    numbers = [] if numbers is None else numbers
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "event_id" and isinstance(v, str):
                events.add(v)
            elif k == "event_ids" and isinstance(v, list):
                events.update(x for x in v if isinstance(x, str))
            else:
                collect(v, events, numbers)
    elif isinstance(obj, list):
        numbers.append(float(len(obj)))
        for v in obj:
            collect(v, events, numbers)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        numbers.append(float(obj))
    return events, numbers
