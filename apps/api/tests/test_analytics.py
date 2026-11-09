"""Day 2 acceptance: stored metrics are verified against the source events, the official scoreboard and match facts."""

import json

import pytest

from app.core.config import ROOT
from app.services import analytics
from app.services.ingest import fetch

SEL = json.loads((ROOT / "data/samples/selected_matches.json").read_text(encoding="utf-8"))
IDS = [m["match_id"] for m in SEL["matches"]]
ON_TARGET = ("Goal", "Saved", "Saved to Post")


def _raw_match(mid):
    return next(x for x in fetch(f"matches/{SEL['competition_id']}/{SEL['season_id']}.json") if x["match_id"] == mid)


@pytest.mark.parametrize("mid", IDS)
def test_goals_equal_official_scoreboard(db, mid):
    raw = _raw_match(mid)
    s = analytics.match_stats(db, mid)
    assert (s["home"]["goals"], s["away"]["goals"]) == (raw["home_score"], raw["away_score"])


@pytest.mark.parametrize("mid", IDS)
def test_team_metrics_recounted_from_raw_events(db, mid):
    events = fetch(f"events/{mid}.json")
    stats = analytics.match_stats(db, mid)
    for side in ("home", "away"):
        t = stats[side]
        mine = [e for e in events if e.get("team", {}).get("id") == t["team_id"]]
        shots = [e for e in mine if e["type"]["name"] == "Shot" and e["period"] != 5]
        passes = [e for e in mine if e["type"]["name"] == "Pass"]
        assert t["shots"] == len(shots)
        assert t["shots_on_target"] == sum(e["shot"]["outcome"]["name"] in ON_TARGET for e in shots)
        assert t["xg"] == pytest.approx(sum(e["shot"]["statsbomb_xg"] for e in shots), abs=0.01)
        assert t["np_xg"] == pytest.approx(
            sum(e["shot"]["statsbomb_xg"] for e in shots if e["shot"]["type"]["name"] != "Penalty"), abs=0.01
        )
        assert t["passes"] == len(passes)
        assert t["passes_completed"] == sum("outcome" not in e["pass"] for e in passes)
        assert t["pressures"] == sum(e["type"]["name"] == "Pressure" for e in mine)
        assert t["fouls_committed"] == sum(e["type"]["name"] == "Foul Committed" for e in mine)


@pytest.mark.parametrize("mid", IDS)
def test_player_stats_sum_to_team_stats(db, mid):
    stats = analytics.match_stats(db, mid)
    players = analytics.player_stats(db, mid)
    for side in ("home", "away"):
        t = stats[side]
        mine = [p for p in players if p["team"] == t["team"]]
        assert sum(p["goals"] for p in mine) == t["goals"]
        assert sum(p["shots"] for p in mine) == t["shots"]
        assert sum(p["xg"] for p in mine) == pytest.approx(t["xg"], abs=0.05)
        assert sum(p["passes"] for p in mine) == t["passes"]
        assert sum(p["assists"] for p in mine) <= t["goals"]


def _goals(db, mid):
    return {p["player"]: p["goals"] for p in analytics.player_stats(db, mid) if p["goals"]}


def test_known_scorers_world_cup_final(db):
    # Argentina 3-3 France (4-2 pens): Messi 2, Di Maria 1, Mbappe 3
    g = _goals(db, 3869685)
    by = lambda frag: next(v for k, v in g.items() if frag in k)
    assert by("Messi") == 2 and by("Di Mar") == 1 and by("Mbapp") == 3 and len(g) == 3


def test_known_scorers_germany_japan_and_saudi(db):
    g = _goals(db, 3857284)  # Germany 1-2 Japan: Gundogan (pen), Doan, Asano
    assert sorted(k.split()[-1] for k in g) == ["Asano", "Doan", "Gündoğan"] and set(g.values()) == {1}
    g = _goals(db, 3857300)  # Argentina 1-2 Saudi Arabia: Messi (pen), Al Shehri, Al Dawsari
    assert len(g) == 3 and any("Messi" in k for k in g) and any("Dawsari" in k for k in g)


def test_penalty_shootout_is_excluded_from_match_numbers(db):
    s = analytics.match_stats(db, 3869685)
    assert (s["home"]["shootout_goals"], s["away"]["shootout_goals"]) == (4, 2)  # Argentina won 4-2 on penalties
    assert s["home"]["goals"] == s["away"]["goals"] == 3  # shootout goals not counted
    assert len(analytics.shot_map(db, 3869685, include_shootout=True)) - len(analytics.shot_map(db, 3869685)) == 8
    assert analytics.match_stats(db, 3857300)["home"]["shootout_goals"] is None  # no shootout in that match


def test_every_shot_is_traceable_to_a_raw_event(db):
    """Evidence check: each shot's event_id exists in the source file with the same player, xG and coordinates."""
    for mid in IDS:
        raw = {e["id"]: e for e in fetch(f"events/{mid}.json")}
        for s in analytics.shot_map(db, mid, include_shootout=True):
            e = raw[s["event_id"]]
            assert e["type"]["name"] == "Shot"
            assert e["player"]["id"] == s["player_id"]
            assert e["shot"].get("statsbomb_xg") == pytest.approx(s["xg"]) if s["xg"] is not None else True
            assert e["location"] == [s["x"], s["y"]]


def test_unknown_match_returns_none(db):
    assert analytics.match_stats(db, 1) is None
    assert analytics.shot_map(db, 1) is None
    assert analytics.player_stats(db, 1) is None
