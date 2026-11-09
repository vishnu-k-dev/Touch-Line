import pytest
from fastapi.testclient import TestClient

from app.main import app

FINAL = 3869685


@pytest.fixture(scope="module")
def client(db):  # `db` fixture guarantees the sample data is loaded
    return TestClient(app)


def test_competitions_and_matches(client):
    comps = client.get("/api/v1/competitions").json()
    assert comps[0]["name"] == "FIFA World Cup" and comps[0]["seasons"][0]["name"] == "2022"
    ms = client.get("/api/v1/matches").json()
    assert len(ms) == 5 and ms == sorted(ms, key=lambda m: (m["date"], m["id"]))
    assert client.get("/api/v1/matches", params={"competition_id": 999}).json() == []


def test_match_detail(client):
    m = client.get(f"/api/v1/matches/{FINAL}").json()
    assert (m["home_team"]["name"], m["away_team"]["name"], m["stage"]) == ("Argentina", "France", "Final")
    assert m["event_count"] == 4407 and m["shot_count"] == 38  # 30 in play + 8 shootout


def test_stats_shots_players(client):
    s = client.get(f"/api/v1/matches/{FINAL}/stats").json()
    assert s["home"]["goals"] == 3 and s["away"]["goals"] == 3 and "xg" in s["definitions"]
    shots = client.get(f"/api/v1/matches/{FINAL}/shots").json()
    assert len(shots) == 30 and all(not x["is_shootout"] for x in shots)
    assert len(client.get(f"/api/v1/matches/{FINAL}/shots", params={"include_shootout": True}).json()) == 38
    players = client.get(f"/api/v1/matches/{FINAL}/players").json()
    assert players[0]["player"].startswith("Kylian Mbapp")  # highest xG in the match


def test_search_endpoint(client, indexed):
    hits = client.get("/api/v1/search", params={"q": "why did the team with higher xG lose", "k": 3}).json()
    assert len(hits) == 3 and hits[0]["title"] == "Why a team can lose despite higher xG"
    assert hits == sorted(hits, key=lambda h: -h["score"])
    seq = client.get("/api/v1/search", params={"q": "chance", "kind": "sequence", "play_pattern": "From Corner", "body_part": "Head", "k": 20}).json()
    assert seq and all(h["meta"]["play_pattern"] == "From Corner" and h["meta"]["body_part"] == "Head" for h in seq)
    assert client.get("/api/v1/search", params={"q": "xg", "kind": "nonsense"}).status_code == 422
    assert client.get("/api/v1/search", params={"q": "x"}).status_code == 422  # too short


@pytest.mark.parametrize("path", ["", "/stats", "/shots", "/players"])
def test_unknown_match_is_404(client, path):
    assert client.get(f"/api/v1/matches/1{path}").status_code == 404
