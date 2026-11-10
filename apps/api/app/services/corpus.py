"""Builds the retrievable documents: tactical knowledge (hand-written), plus match summaries and shot sequences
generated deterministically from the stored events, so every generated sentence is a measured fact."""

import math
import re
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ROOT
from app.models.tables import Event, Match, Player, Shot, Team
from app.services import analytics

KNOWLEDGE_FILE = ROOT / "data" / "knowledge" / "tactical_knowledge.md"

PATTERN = {
    "Regular Play": "open play", "From Counter": "a counter-attack", "From Corner": "a corner",
    "From Free Kick": "a free kick", "From Throw In": "a throw-in", "From Goal Kick": "a goal kick",
    "From Keeper": "the goalkeeper's distribution", "From Kick Off": "the kick-off", "Other": "a loose ball",
}
OUTCOME = {
    "Goal": "a goal was scored", "Saved": "the goalkeeper saved it", "Saved Off Target": "it was saved but was going off target",
    "Blocked": "a defender blocked it", "Off T": "it missed the target", "Wayward": "it flew wide of the target",
    "Post": "it hit the post",
}


def knowledge_docs() -> list[dict]:
    text = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    docs = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:  # [0] is the file header
        title, _, body = block.partition("\n")
        docs.append({"kind": "knowledge", "title": title.strip(), "content": body.strip(), "match_id": None, "meta": {}})
    return docs


def _match_doc(m: Match, s: dict) -> dict:
    h, a = s["home"], s["away"]
    title = f"{h['team']} {h['goals']}-{a['goals']} {a['team']} ({m.stage})"
    if h["goals"] == a["goals"]:
        outcome = "It finished as a goalless draw." if h["goals"] == 0 else f"It finished as a {h['goals']}-{a['goals']} draw."
    else:
        win, lose = (h, a) if h["goals"] > a["goals"] else (a, h)
        outcome = f"{win['team']} beat {lose['team']} {win['goals']}-{lose['goals']}; {lose['team']} were defeated."
    parts = [
        f"{title}, {m.match_date:%d %B %Y}. {outcome}",
        f"Shots: {h['team']} {h['shots']} (xG {h['xg']:.2f}, {h['shots_on_target']} on target), "
        f"{a['team']} {a['shots']} (xG {a['xg']:.2f}, {a['shots_on_target']} on target).",
        f"Pass share {h['pass_share_pct']}% to {a['pass_share_pct']}%. Pressures {h['pressures']} to {a['pressures']}.",
    ]
    if h["xg"] != a["xg"]:
        lead, other = (h, a) if h["xg"] > a["xg"] else (a, h)
        result = "won" if lead["goals"] > other["goals"] else "drew" if lead["goals"] == other["goals"] else "lost"
        parts.append(
            f"{lead['team']} had the higher xG ({lead['xg']:.2f} to {other['xg']:.2f}) and {result} the match"
            + (" despite creating more expected goals." if result == "lost" else ".")
        )
    if h["shootout_goals"] is not None:
        parts.append(f"The match went to a penalty shootout: {h['team']} {h['team']} {h['shootout_goals']}-{a['shootout_goals']} {a['team']}.")
    return {
        "kind": "match", "title": title, "content": " ".join(parts), "match_id": m.id,
        "meta": {"home": h["team"], "away": a["team"], "stage": m.stage},
    }


def _place(x: float, y: float) -> str:
    if x >= 114 and 30 <= y <= 50:
        return "inside the six-yard box"
    if x >= 102 and 18 <= y <= 62:
        return "inside the penalty area"
    return "outside the penalty area"


def sequence_docs(db: Session, m: Match) -> list[dict]:
    # Light rows only (no raw_data): a match has ~4,000 events and their JSON is what made this step run out of memory on a
    # 512 MB host. The raw JSON is fetched below for the shots alone.
    events = db.execute(
        select(Event.id, Event.idx, Event.type, Event.team_id, Event.player_id, Event.minute, Event.second, Event.possession)
        .where(Event.match_id == m.id).order_by(Event.idx)
    ).all()
    by_id = {e.id: e for e in events}
    by_possession = defaultdict(list)
    for e in events:
        by_possession[e.possession].append(e)
    players = {p.id: p.name for p in db.scalars(select(Player))}
    teams = {t.id: t.name for t in db.scalars(select(Team))}
    score = f"{m.home_team.name} {m.home_score}-{m.away_score} {m.away_team.name}"
    shots = db.scalars(
        select(Shot).where(Shot.match_id == m.id, Shot.is_shootout.is_(False)).order_by(Shot.period, Shot.minute, Shot.second)
    )
    shots = list(shots)
    shot_json = dict(db.execute(select(Event.id, Event.raw_data).where(Event.id.in_([s.event_id for s in shots]))).all())
    docs = []
    for s in shots:
        ev = by_id[s.event_id]
        raw = shot_json[s.event_id]
        own = [e for e in by_possession[ev.possession] if e.team_id == s.team_id and e.idx < ev.idx]
        passes = sum(e.type == "Pass" for e in own)
        secs = (ev.minute * 60 + ev.second) - (own[0].minute * 60 + own[0].second) if own else 0
        pattern = raw["play_pattern"]["name"]
        key = by_id.get(raw["shot"].get("key_pass_id"))
        dist = math.hypot(120 - s.x, 40 - s.y)
        took = {"Penalty": "took a penalty kick", "Free Kick": "took a direct free kick"}.get(s.shot_type, "had a shot")
        body = {"Head": "with a header", "Right Foot": "with the right foot", "Left Foot": "with the left foot"}.get(
            s.body_part, "with another body part"
        )
        build = (
            "no completed passes before the shot" if passes == 0 else
            f"a quick, direct move of {passes} pass{'es' if passes > 1 else ''}" if passes <= 2 else
            f"a patient build-up of {passes} passes" if passes >= 8 else f"a move of {passes} passes"
        )
        origin = (
            "It was a penalty."  # no build-up to describe
            if s.shot_type == "Penalty"
            else f"The possession began from {PATTERN.get(pattern, pattern)} with {build} over {secs} seconds"
            + (f", set up by {players[key.player_id]}" if key and key.player_id else "") + "."
        )
        when = f"{s.minute}'" + (" in extra time" if s.period >= 3 else "") + (" late in the game" if s.minute >= 80 and s.period < 3 else "")
        team, player = teams[s.team_id], players[s.player_id]
        lane = (  # 360 freeze-frame fact, stated only when the whole shooting lane was in the camera's view
            f" Freeze-frame: {'no visible defenders' if s.defenders_in_cone == 0 else f'{s.defenders_in_cone} visible defender' + ('s' if s.defenders_in_cone > 1 else '')}"
            " in the shooting lane."
            if s.cone_visible else ""
        )
        content = (
            f"{team} chance at {when}: {player} {took} {body}; {OUTCOME.get(s.outcome, s.outcome)} (xG {(s.xg or 0):.2f}). "
            f"It was {dist:.0f} yards from goal, {_place(s.x, s.y)}, "
            f"{'central' if 26.7 <= s.y <= 53.3 else 'from a wide angle'}.{lane} "
            f"{origin} Match: {score} ({m.stage})."
        )
        docs.append(
            {
                "kind": "sequence", "title": f"{team} {s.minute}' {player} ({s.outcome})", "content": content, "match_id": m.id,
                "meta": {
                    "event_ids": [s.event_id] + ([key.id] if key else []), "team": team, "player": player,
                    "minute": s.minute, "period": s.period, "xg": s.xg, "outcome": s.outcome, "shot_type": s.shot_type,
                    "body_part": s.body_part, "play_pattern": pattern, "distance": round(dist, 1), "passes": passes,
                    "defenders_in_cone": s.defenders_in_cone if s.cone_visible else None,
                },
            }
        )
    return docs


def build_corpus(db: Session) -> list[dict]:
    docs = knowledge_docs()
    for m in db.scalars(select(Match).order_by(Match.match_date, Match.id)):
        docs.append(_match_doc(m, analytics.match_stats(db, m.id)))
        docs.extend(sequence_docs(db, m))
    return docs
