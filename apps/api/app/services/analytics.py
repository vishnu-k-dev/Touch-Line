"""Football metrics computed from stored StatsBomb events. Every number here is reproducible from the raw event JSON
(see tests/, which recount from the raw files)."""

import copy
import functools
import threading
import time
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Event, Match, Player, PlayerMinutes, Shot, Team

SHOT_ON_TARGET = {"Goal", "Saved", "Saved to Post"}

# Match data is static once ingested, but each metric rereads thousands of raw events (~50 ms alone, seconds when many
# visitors arrive together). So results are cached for a while; a lock per key makes a burst of first requests compute
# each answer once. ponytail: in-process, per instance. After re-ingesting, restart the API or wait out the TTL.
CACHE_TTL_SECONDS = 600
_cache: dict = {}
_key_locks: dict = {}


def clear_cache() -> None:
    _cache.clear()


def cached(fn):
    @functools.wraps(fn)
    def wrapper(db, *args, **kwargs):
        key = (fn.__name__, args, tuple(sorted(kwargs.items())))

        def fresh():
            hit = _cache.get(key)
            return hit[1] if hit and hit[0] > time.monotonic() else None

        if (value := fresh()) is not None:
            return copy.deepcopy(value)
        with _key_locks.setdefault(key, threading.Lock()):
            if (value := fresh()) is None:
                value = fn(db, *args, **kwargs)
                if value is not None:  # unknown matches are not cached
                    _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, copy.deepcopy(value))
        return copy.deepcopy(value)

    return wrapper

# PPDA zone, in each team's own coordinates (every team attacks toward x=120): the pressing team's attacking 60%
# is x >= 48; the same stretch of pitch is the opponent's own 60%, i.e. x <= 72 in the opponent's coordinates.
PPDA_PRESS_ZONE_X = 48.0
PPDA_BUILD_ZONE_X = 72.0

HEATMAP_COLS, HEATMAP_ROWS, HEATMAP_CELL = 12, 8, 10.0  # 120 x 80 pitch in 10-yard cells
HEATMAP_KINDS = {
    "actions": {"Pass", "Ball Receipt*", "Carry", "Dribble", "Shot", "Duel", "Ball Recovery", "Interception",
                "Clearance", "Block", "Miscontrol", "Dispossessed"},
    "passes": {"Pass"},
    "pressures": {"Pressure"},
    "shots": {"Shot"},
}

DEFINITIONS = {
    "goals": "Goals from shots in periods 1-4 plus own goals in favour. Penalty-shootout kicks excluded.",
    "shots": "Shot events in periods 1-4. Penalty-shootout kicks excluded.",
    "shots_on_target": "Shots with outcome Goal, Saved or Saved to Post.",
    "xg": "Sum of StatsBomb xG over those shots, penalties included.",
    "np_xg": "xG excluding penalties.",
    "passes_completed": "Passes with no outcome recorded (StatsBomb only logs outcomes for failed passes).",
    "pass_share_pct": "Team's share of all passes in the match. A proxy for possession, not time-based possession.",
    "pressures": "Pressure events logged for the team.",
    "ppda": "Passes allowed per defensive action: opponent passes made in their own 60% of the pitch divided by this team's "
            "defensive actions (tackles, interceptions, fouls committed, dribbled-past challenges) in the opponent's 60%. "
            "Lower means a more intense press. Periods 1-4. Null if there were no defensive actions in the zone.",
    "shootout_goals": "Goals scored in the penalty shootout (period 5); null if the match had none.",
}


def _shots(db: Session, match_id: int) -> list[Shot]:
    return list(db.scalars(select(Shot).where(Shot.match_id == match_id)))


def _is_defensive_action(ty: str, raw: dict) -> bool:
    return ty in ("Interception", "Foul Committed", "Dribbled Past") or (
        ty == "Duel" and raw["duel"].get("type", {}).get("name") == "Tackle"
    )


@cached
def match_stats(db: Session, match_id: int) -> dict | None:
    m = db.get(Match, match_id)
    if m is None:
        return None
    shots = _shots(db, match_id)
    rows = db.execute(
        select(Event.type, Event.team_id, Event.raw_data, Event.x, Event.period).where(
            Event.match_id == match_id,
            Event.type.in_(["Pass", "Pressure", "Foul Committed", "Own Goal For", "Duel", "Interception", "Dribbled Past"]),
        )
    ).all()
    total_passes = sum(1 for ty, *_ in rows if ty == "Pass")

    def team(t: Team, opp: Team) -> dict:
        reg = [s for s in shots if s.team_id == t.id and not s.is_shootout]
        shootout = [s for s in shots if s.team_id == t.id and s.is_shootout]
        mine = [(ty, raw) for ty, tid, raw, *_ in rows if tid == t.id]
        passes = [raw["pass"] for ty, raw in mine if ty == "Pass"]
        done = sum("outcome" not in p for p in passes)
        xg = sum(s.xg or 0 for s in reg)
        allowed = sum(
            1 for ty, tid, _, x, per in rows
            if ty == "Pass" and tid == opp.id and per <= 4 and x is not None and x <= PPDA_BUILD_ZONE_X
        )
        actions = sum(
            1 for ty, tid, raw, x, per in rows
            if tid == t.id and per <= 4 and x is not None and x >= PPDA_PRESS_ZONE_X and _is_defensive_action(ty, raw)
        )
        return {
            "team_id": t.id,
            "team": t.name,
            "goals": sum(s.outcome == "Goal" for s in reg) + sum(ty == "Own Goal For" for ty, _ in mine),
            "shots": len(reg),
            "shots_on_target": sum(s.outcome in SHOT_ON_TARGET for s in reg),
            "xg": round(xg, 2),
            "np_xg": round(sum(s.xg or 0 for s in reg if s.shot_type != "Penalty"), 2),
            "xg_per_shot": round(xg / len(reg), 3) if reg else 0.0,
            "passes": len(passes),
            "passes_completed": done,
            "pass_accuracy_pct": round(100 * done / len(passes), 1) if passes else 0.0,
            "pass_share_pct": round(100 * len(passes) / total_passes, 1) if total_passes else 0.0,
            "pressures": sum(ty == "Pressure" for ty, _ in mine),
            "fouls_committed": sum(ty == "Foul Committed" for ty, _ in mine),
            "corners": sum(p.get("type", {}).get("name") == "Corner" for p in passes),
            "ppda": round(allowed / actions, 2) if actions else None,
            "ppda_passes_allowed": allowed,
            "ppda_defensive_actions": actions,
            "shootout_goals": sum(s.outcome == "Goal" for s in shootout) if shootout else None,
        }

    return {
        "match_id": match_id,
        "home": team(m.home_team, m.away_team),
        "away": team(m.away_team, m.home_team),
        "definitions": DEFINITIONS,
    }


@cached
def shot_map(db: Session, match_id: int, include_shootout: bool = False) -> list[dict] | None:
    if db.get(Match, match_id) is None:
        return None
    q = (
        select(Shot, Player.name, Player.nickname, Team.name)
        .join(Player, Player.id == Shot.player_id)
        .join(Team, Team.id == Shot.team_id)
        .where(Shot.match_id == match_id)
        .order_by(Shot.period, Shot.minute, Shot.second)
    )
    if not include_shootout:
        q = q.where(Shot.is_shootout.is_(False))
    return [
        {
            "event_id": s.event_id, "team_id": s.team_id, "team": team, "player_id": s.player_id, "player": player,
            "display_name": nickname or player, "period": s.period, "minute": s.minute, "second": s.second, "x": s.x, "y": s.y, "xg": s.xg,
            "outcome": s.outcome, "shot_type": s.shot_type, "body_part": s.body_part, "is_shootout": s.is_shootout,
            "defenders_in_cone": s.defenders_in_cone, "cone_visible": s.cone_visible,
            "nearest_defender": s.nearest_defender,
        }
        for s, player, nickname, team in db.execute(q)
    ]


_COLS = ["shots", "goals", "xg", "np_xg", "passes", "passes_completed", "key_passes", "assists",
         "pressures", "tackles", "interceptions"]


@cached
def player_stats(db: Session, match_id: int) -> list[dict] | None:
    if db.get(Match, match_id) is None:
        return None
    stats: dict[int, dict] = defaultdict(lambda: dict.fromkeys(_COLS, 0))
    for s in _shots(db, match_id):
        if s.is_shootout:
            continue
        p = stats[s.player_id]
        p["shots"] += 1
        p["goals"] += s.outcome == "Goal"
        p["xg"] += s.xg or 0
        p["np_xg"] += (s.xg or 0) if s.shot_type != "Penalty" else 0
    events = db.execute(
        select(Event.type, Event.player_id, Event.raw_data).where(
            Event.match_id == match_id,
            Event.player_id.is_not(None),
            Event.type.in_(["Pass", "Pressure", "Duel", "Interception"]),
        )
    )
    for ty, pid, raw in events:
        p = stats[pid]
        if ty == "Pass":
            p["passes"] += 1
            p["passes_completed"] += "outcome" not in raw["pass"]
            p["key_passes"] += bool(raw["pass"].get("shot_assist"))
            p["assists"] += bool(raw["pass"].get("goal_assist"))
        elif ty == "Pressure":
            p["pressures"] += 1
        elif ty == "Duel":
            p["tackles"] += raw["duel"].get("type", {}).get("name") == "Tackle"
        else:
            p["interceptions"] += 1

    names = {p.id: p for p in db.scalars(select(Player).where(Player.id.in_(stats)))}
    teams = {t.id: t.name for t in db.scalars(select(Team))}
    played = {
        r.player_id: r for r in db.scalars(select(PlayerMinutes).where(PlayerMinutes.match_id == match_id))
    }
    out = [
        {
            "player_id": pid, "player": names[pid].name, "display_name": names[pid].nickname or names[pid].name,
            "team": teams.get(names[pid].team_id), **s,
            "xg": round(s["xg"], 2), "np_xg": round(s["np_xg"], 2),
            "minutes": round(played[pid].minutes, 1) if pid in played else 0.0,
            "started": played[pid].started if pid in played else False,
        }
        for pid, s in stats.items()
    ]
    return sorted(out, key=lambda r: (-r["xg"], -r["goals"], -r["passes"]))


@cached
def heatmap(
    db: Session, match_id: int, team_id: int | None = None, player_id: int | None = None, kind: str = "actions"
) -> dict | None:
    """Counts of a player's (or team's) actions per 10-yard cell of the pitch, periods 1-4.
    `cells[row][col]`: col 0..11 along the pitch toward the opponent's goal (x), row 0..7 across it (y)."""
    if db.get(Match, match_id) is None:
        return None
    if kind not in HEATMAP_KINDS:
        raise ValueError(f"kind must be one of {sorted(HEATMAP_KINDS)}")
    q = select(Event.x, Event.y).where(
        Event.match_id == match_id, Event.type.in_(HEATMAP_KINDS[kind]), Event.period <= 4,
        Event.x.is_not(None), Event.y.is_not(None),
    )
    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    if player_id is not None:
        q = q.where(Event.player_id == player_id)
    cells = [[0] * HEATMAP_COLS for _ in range(HEATMAP_ROWS)]
    for x, y in db.execute(q):
        cells[min(int(y // HEATMAP_CELL), HEATMAP_ROWS - 1)][min(int(x // HEATMAP_CELL), HEATMAP_COLS - 1)] += 1
    return {
        "match_id": match_id, "team_id": team_id, "player_id": player_id, "kind": kind,
        "cols": HEATMAP_COLS, "rows": HEATMAP_ROWS, "cell_yards": HEATMAP_CELL,
        "total": sum(map(sum, cells)), "max": max(map(max, cells)), "cells": cells,
    }
