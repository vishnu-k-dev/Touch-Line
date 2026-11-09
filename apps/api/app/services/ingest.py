"""Load StatsBomb Open Data into Postgres.

    cd apps/api && python -m app.services.ingest            # reload the matches in data/samples/selected_matches.json
    cd apps/api && python -m app.services.ingest 3869685    # reload specific match ids (same competition)

Idempotent: re-running replaces a match's events and shots. Missing raw files are downloaded into data/raw/.
"""

import json
import sys
from datetime import date

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import ROOT
from app.core.db import SessionLocal, init_db
from app.models.tables import Competition, Event, Match, Player, PlayerMinutes, Season, Shot, Team
from app.services import analytics
from app.services.geometry import shot_context

RAW = ROOT / "data" / "raw"
SELECTED = ROOT / "data" / "samples" / "selected_matches.json"
BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def fetch(rel: str):
    """Return parsed JSON for a StatsBomb data file, downloading it to data/raw/ if not cached."""
    path = RAW / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        r = httpx.get(f"{BASE_URL}/{rel}", timeout=60, follow_redirects=True)
        r.raise_for_status()
        path.write_bytes(r.content)
    return json.loads(path.read_text(encoding="utf-8"))


PERIOD_START_CLOCK = {1: 0.0, 2: 45.0, 3: 90.0, 4: 105.0}  # StatsBomb match clock at the start of each period


def compute_minutes(lineups: list[dict], events: list[dict]) -> list[dict]:
    """Minutes played per squad player, in real elapsed time (periods 1-4).

    Built from Starting XI, Substitution and red-card events, not from lineup position spells: the spells are
    inconsistent in extra-time matches (backwards spells, substituted-off players recorded as playing on). The events
    pass an exact consistency check: each team's minutes sum to 11 x match length when nobody is sent off.

    The match clock restarts in extra time (period 3 begins at 90:00), so times are converted to elapsed minutes
    using each period's true length from its Half End event. Lineups supply the full squad (unused substitutes get 0)."""
    ends = {e["period"]: e["minute"] + e["second"] / 60 for e in events if e["type"]["name"] == "Half End" and e["period"] <= 4}
    before, total = {}, 0.0
    for p in sorted(ends):
        before[p] = total
        total += ends[p] - PERIOD_START_CLOCK[p]

    def elapsed(e: dict) -> float:
        return before[e["period"]] + e["minute"] + e["second"] / 60 - PERIOD_START_CLOCK[e["period"]]

    on, off = {}, {}
    for e in events:
        kind = e["type"]["name"]
        if kind == "Starting XI":
            on.update({pl["player"]["id"]: 0.0 for pl in e["tactics"]["lineup"]})
        elif e["period"] > 4:
            continue
        elif kind == "Substitution":
            off[e["player"]["id"]] = elapsed(e)
            on[e["substitution"]["replacement"]["id"]] = elapsed(e)
        else:
            card = (e.get("foul_committed") or e.get("bad_behaviour") or {}).get("card", {}).get("name")
            if card in ("Red Card", "Second Yellow"):
                off[e["player"]["id"]] = elapsed(e)

    return [
        {
            "player_id": pl["player_id"], "team_id": team["team_id"], "jersey_number": pl["jersey_number"],
            "minutes": round(off.get(pl["player_id"], total) - on[pl["player_id"]], 2) if pl["player_id"] in on else 0.0,
            "started": on.get(pl["player_id"]) == 0.0,
        }
        for team in lineups
        for pl in team["lineup"]
    ]

def fetch_optional(rel: str):
    """Like fetch, but None when the file does not exist upstream (e.g. a match without 360 data)."""
    try:
        return fetch(rel)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


def _insert_ignore(db, model, rows):
    if rows:
        db.execute(pg_insert(model).values(rows).on_conflict_do_nothing())


def ingest_match(db, competition_id: int, season_id: int, match_id: int) -> int:
    comp = next(
        c for c in fetch("competitions.json") if c["competition_id"] == competition_id and c["season_id"] == season_id
    )
    m = next(x for x in fetch(f"matches/{competition_id}/{season_id}.json") if x["match_id"] == match_id)
    events = fetch(f"events/{match_id}.json")
    lineups = fetch(f"lineups/{match_id}.json")
    frames = {f["event_uuid"]: f for f in fetch_optional(f"three-sixty/{match_id}.json") or []}
    home, away = m["home_team"], m["away_team"]

    _insert_ignore(db, Competition, [{"id": competition_id, "name": comp["competition_name"], "country": comp["country_name"]}])
    _insert_ignore(db, Season, [{"competition_id": competition_id, "id": season_id, "name": comp["season_name"]}])
    _insert_ignore(
        db,
        Team,
        [
            {"id": home["home_team_id"], "name": home["home_team_name"]},
            {"id": away["away_team_id"], "name": away["away_team_name"]},
        ],
    )

    players = {}  # lineups carry nicknames; fall back to events for anyone missing from them
    for t in lineups:
        for p in t["lineup"]:
            players[p["player_id"]] = {
                "id": p["player_id"], "name": p["player_name"], "nickname": p["player_nickname"], "team_id": t["team_id"],
            }
    for e in events:
        if "player" in e:
            players.setdefault(
                e["player"]["id"],
                {"id": e["player"]["id"], "name": e["player"]["name"], "nickname": None, "team_id": e["team"]["id"]},
            )
    _insert_ignore(db, Player, list(players.values()))

    db.execute(delete(PlayerMinutes).where(PlayerMinutes.match_id == match_id))
    db.execute(delete(Shot).where(Shot.match_id == match_id))
    db.execute(delete(Event).where(Event.match_id == match_id))
    db.merge(
        Match(
            id=match_id,
            competition_id=competition_id,
            season_id=season_id,
            match_date=date.fromisoformat(m["match_date"]),
            stage=m["competition_stage"]["name"],
            home_team_id=home["home_team_id"],
            away_team_id=away["away_team_id"],
            home_score=m["home_score"],
            away_score=m["away_score"],
        )
    )
    db.flush()

    event_rows, shot_rows = [], []
    for e in events:
        x, y = (e.get("location") or [None, None])[:2]
        event_rows.append(
            {
                "id": e["id"], "match_id": match_id, "idx": e["index"], "period": e["period"],
                "minute": e["minute"], "second": e["second"], "type": e["type"]["name"],
                "team_id": e.get("team", {}).get("id"), "player_id": e.get("player", {}).get("id"),
                "x": x, "y": y, "possession": e["possession"], "raw_data": e,
            }
        )
        if e["type"]["name"] == "Shot":
            s = e["shot"]
            ctx = shot_context((x, y), frames[e["id"]]) if e["id"] in frames and x is not None else {}
            shot_rows.append(
                {
                    "event_id": e["id"], "match_id": match_id, "team_id": e["team"]["id"], "player_id": e["player"]["id"],
                    "period": e["period"], "minute": e["minute"], "second": e["second"], "x": x, "y": y,
                    "xg": s.get("statsbomb_xg"), "outcome": s["outcome"]["name"],
                    "shot_type": s.get("type", {}).get("name"), "body_part": s.get("body_part", {}).get("name"),
                    "technique": s.get("technique", {}).get("name"), "is_shootout": e["period"] == 5,
                    "defenders_in_cone": ctx.get("defenders_in_cone"), "cone_visible": ctx.get("cone_visible"),
                    "nearest_defender": ctx.get("nearest_defender"),
                }
            )
    db.execute(insert(Event), event_rows)
    db.execute(insert(Shot), shot_rows)
    db.execute(insert(PlayerMinutes), [{"match_id": match_id, **r} for r in compute_minutes(lineups, events)])
    analytics.clear_cache()
    return len(event_rows)


def ingest_selected(match_ids: list[int] | None = None, force: bool = True) -> None:
    """Ingest the sample matches (or `match_ids`). With force=False, matches already loaded are skipped."""
    cfg = json.loads(SELECTED.read_text(encoding="utf-8"))
    ids = match_ids or [m["match_id"] for m in cfg["matches"]]
    init_db()
    with SessionLocal() as db:
        for mid in ids:
            if not force and db.scalar(select(func.count()).select_from(Event).where(Event.match_id == mid)):
                continue
            n = ingest_match(db, cfg["competition_id"], cfg["season_id"], mid)
            db.commit()
            print(f"match {mid}: {n} events loaded")


if __name__ == "__main__":
    ingest_selected([int(a) for a in sys.argv[1:]] or None)
