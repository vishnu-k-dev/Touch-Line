"""Minutes played, PPDA, heatmaps and 360 shot context, each recounted from the raw StatsBomb files."""

import json
from math import atan2, pi

import pytest
from sqlalchemy import select

from app.core.config import ROOT
from app.models.tables import PlayerMinutes, Shot
from app.services import analytics
from app.services.geometry import in_polygon, in_triangle
from app.services.ingest import fetch

SEL = json.loads((ROOT / "data/samples/selected_matches.json").read_text(encoding="utf-8"))
IDS = [m["match_id"] for m in SEL["matches"]]
FINAL = 3869685
START = {1: 0.0, 2: 45.0, 3: 90.0, 4: 105.0}


def _match_length(events):
    """Real playing time in minutes, from each period's Half End clock."""
    ends = {e["period"]: e["minute"] + e["second"] / 60 for e in events if e["type"]["name"] == "Half End" and e["period"] <= 4}
    return sum(ends[p] - START[p] for p in ends)


# ---------- minutes played ----------
@pytest.mark.parametrize("mid", IDS)
def test_each_team_has_eleven_players_on_for_the_whole_match(db, mid):
    length = _match_length(fetch(f"events/{mid}.json"))
    rows = list(db.scalars(select(PlayerMinutes).where(PlayerMinutes.match_id == mid)))
    for team in {r.team_id for r in rows}:
        mine = [r for r in rows if r.team_id == team]
        assert sum(r.minutes for r in mine) == pytest.approx(11 * length, abs=0.5)  # no red cards in these matches
        assert sum(r.started for r in mine) == 11
        assert all(0 <= r.minutes <= length + 0.01 for r in mine)


def test_substitutes_match_substitution_events(db):
    events = fetch(f"events/{FINAL}.json")
    subs_on = {e["substitution"]["replacement"]["id"] for e in events if e["type"]["name"] == "Substitution" and e["period"] <= 4}
    rows = list(db.scalars(select(PlayerMinutes).where(PlayerMinutes.match_id == FINAL)))
    assert {r.player_id for r in rows if r.minutes > 0 and not r.started} == subs_on


def test_known_minutes_in_the_final(db):
    length = _match_length(fetch(f"events/{FINAL}.json"))
    stats = {p["player"]: p for p in analytics.player_stats(db, FINAL)}
    messi = next(p for n, p in stats.items() if "Messi" in n)
    dybala = next(p for n, p in stats.items() if "Dybala" in n)
    assert messi["minutes"] == pytest.approx(length, abs=0.1) and messi["started"]  # played every minute, incl. extra time
    assert 0 < dybala["minutes"] < 5 and not dybala["started"]  # came on for the end of extra time


# ---------- PPDA ----------
DEFENSIVE = {"Interception", "Foul Committed", "Dribbled Past"}


@pytest.mark.parametrize("mid", IDS)
def test_ppda_recounted_from_raw_events(db, mid):
    events = fetch(f"events/{mid}.json")
    stats = analytics.match_stats(db, mid)
    for me, opp in (("home", "away"), ("away", "home")):
        t, o = stats[me], stats[opp]
        allowed = sum(
            e["type"]["name"] == "Pass" and e["team"]["id"] == o["team_id"] and e["period"] <= 4 and e["location"][0] <= 72
            for e in events
        )
        actions = sum(
            e.get("team", {}).get("id") == t["team_id"] and e["period"] <= 4 and "location" in e and e["location"][0] >= 48
            and (e["type"]["name"] in DEFENSIVE or (e["type"]["name"] == "Duel" and e["duel"].get("type", {}).get("name") == "Tackle"))
            for e in events
        )
        assert (t["ppda_passes_allowed"], t["ppda_defensive_actions"]) == (allowed, actions)
        assert t["ppda"] == pytest.approx(allowed / actions, abs=0.01)


def test_ppda_reflects_a_deep_block(db):
    # Morocco-Spain: Morocco defended deep and let Spain pass (Spain had most of the ball); Spain pressed far more.
    s = analytics.match_stats(db, 3869220)
    assert s["home"]["team"] == "Morocco" and s["home"]["ppda"] > 2 * s["away"]["ppda"]
    assert s["away"]["pass_share_pct"] > 65


# ---------- heatmaps ----------
def _raw_actions(events, kinds, **match):
    return [
        e for e in events
        if e["type"]["name"] in kinds and e["period"] <= 4 and "location" in e
        and all((e.get("player", {}) if k == "player_id" else e.get("team", {})).get("id") == v for k, v in match.items())
    ]


def test_heatmap_counts_equal_raw_event_counts(db):
    events = fetch(f"events/{FINAL}.json")
    messi_id = next(p["player_id"] for p in analytics.player_stats(db, FINAL) if "Messi" in p["player"])
    h = analytics.heatmap(db, FINAL, player_id=messi_id, kind="actions")
    assert h["total"] == len(_raw_actions(events, analytics.HEATMAP_KINDS["actions"], player_id=messi_id))
    assert (h["rows"], h["cols"]) == (8, 12) and len(h["cells"]) == 8 and all(len(r) == 12 for r in h["cells"])
    assert sum(map(sum, h["cells"])) == h["total"] and h["max"] == max(map(max, h["cells"]))
    team = analytics.heatmap(db, FINAL, team_id=779, kind="pressures")
    assert team["total"] == len(_raw_actions(events, {"Pressure"}, team_id=779))
    shots = analytics.heatmap(db, FINAL, team_id=779, kind="shots")
    assert shots["total"] == analytics.match_stats(db, FINAL)["home"]["shots"] + 0  # Argentina is home; shootout excluded


def test_heatmap_cell_placement(db):
    ev = fetch(f"events/{FINAL}.json")
    shot = next(e for e in ev if e["type"]["name"] == "Shot" and e["period"] == 1 and e["team"]["id"] == 779)
    x, y = shot["location"]
    h = analytics.heatmap(db, FINAL, player_id=shot["player"]["id"], kind="shots")
    assert h["cells"][min(int(y // 10), 7)][min(int(x // 10), 11)] >= 1
    with pytest.raises(ValueError):
        analytics.heatmap(db, FINAL, team_id=779, kind="vibes")


# ---------- 360 shot context ----------
def _winding_inside(p, flat):
    """Point-in-polygon by winding number (deliberately a different algorithm from the ray casting in the code)."""
    pts = list(zip(flat[0::2], flat[1::2]))
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a1, a2 = atan2(y1 - p[1], x1 - p[0]), atan2(y2 - p[1], x2 - p[0])
        d = a2 - a1
        d = d - 2 * pi if d > pi else d + 2 * pi if d < -pi else d
        total += d
    return abs(total) > pi


def _area(a, b, c):
    return abs((a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])) / 2)


def _in_triangle_by_area(p, a, b, c):
    return abs(_area(a, b, c) - (_area(p, b, c) + _area(a, p, c) + _area(a, b, p))) < 1e-9 and min(
        _area(p, b, c), _area(a, p, c), _area(a, b, p)) > 1e-9


@pytest.mark.parametrize("mid", IDS)
def test_shot_context_recomputed_from_raw_360(db, mid):
    frames = {f["event_uuid"]: f for f in fetch(f"three-sixty/{mid}.json")}
    raw = {e["id"]: e for e in fetch(f"events/{mid}.json")}
    shots = list(db.scalars(select(Shot).where(Shot.match_id == mid)))
    seen = 0
    for s in shots:
        f = frames.get(s.event_id)
        if f is None:
            assert s.defenders_in_cone is None and s.cone_visible is None
            continue
        seen += 1
        shooter = tuple(raw[s.event_id]["location"][:2])
        opp = [p["location"] for p in f["freeze_frame"] if not p["teammate"] and not p["keeper"]]
        assert s.defenders_in_cone == sum(_in_triangle_by_area(o, shooter, (120, 36), (120, 44)) for o in opp)
        assert s.cone_visible == all(_winding_inside(q, f["visible_area"]) for q in (shooter, (119.5, 36), (119.5, 44)))
    assert seen >= len(shots) - 3  # nearly every shot has a freeze-frame


def test_360_context_is_informative(db):
    """Domain check: shots with several defenders in the lane are worth less xG than shots with a clear lane."""
    rows = [(s.defenders_in_cone, s.xg) for s in db.scalars(select(Shot).where(Shot.is_shootout.is_(False)))
            if s.cone_visible]
    clear = [xg for n, xg in rows if n == 0]
    crowded = [xg for n, xg in rows if n >= 2]
    assert len(clear) > 30 and len(crowded) > 5
    assert sum(clear) / len(clear) > 2 * (sum(crowded) / len(crowded))


def test_geometry_helpers():
    assert in_triangle((110, 40), (100, 40), (120, 36), (120, 44))
    assert not in_triangle((110, 50), (100, 40), (120, 36), (120, 44))
    assert not in_triangle((110, 40), (110, 40), (120, 36), (120, 44))  # on a vertex is not inside
    square = [0, 0, 10, 0, 10, 10, 0, 10]
    assert in_polygon((5, 5), square) and not in_polygon((15, 5), square)
