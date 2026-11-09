"""Chat history persists per anonymous visitor, and hosted-database URLs and CORS are handled."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from agent_helpers import ScriptedProvider, answer, submit, tool_use
from app.api import routes
from app.api.routes import get_provider
from app.core.config import Settings
from app.core.db import SessionLocal
from app.core.limits import Limiter, get_limiter
from app.main import app
from app.models.tables import ChatTurn

A, B = "test-visitor-aaaa1111", "test-visitor-bbbb2222"
MATCH = 3857300


def scripted():
    return ScriptedProvider([tool_use(("list_matches", {})), submit(answer(limitations=["demo"]))])


@pytest.fixture
def client(db):
    app.dependency_overrides[get_limiter] = lambda: Limiter(1000, 1000, 1e9, 10)
    app.dependency_overrides[get_provider] = scripted
    yield TestClient(app)
    app.dependency_overrides.clear()
    with SessionLocal() as s:
        s.execute(delete(ChatTurn).where(ChatTurn.visitor_id.like("test-visitor-%")))
        s.commit()


def ask(client, q="a valid question", visitor=A, match=MATCH):
    headers = {"X-Visitor-Id": visitor} if visitor else {}
    return client.post("/api/v1/analyst/chat", json={"question": q, "match_id": match}, headers=headers)


def history(client, visitor=A, **params):
    return client.get("/api/v1/analyst/history", params=params, headers={"X-Visitor-Id": visitor} if visitor else {}).json()


def test_a_question_and_its_full_result_are_saved_and_come_back(client):
    r = ask(client, "Why did Argentina lose?")
    assert r.status_code == 200
    turns = history(client)
    assert len(turns) == 1 and turns[0]["question"] == "Why did Argentina lose?" and turns[0]["match_id"] == MATCH
    saved = turns[0]["result"]
    assert saved["status"] == "answered" and saved["answer"]["limitations"] == ["demo"] and saved["trace"][0]["tool"] == "list_matches"
    assert saved["usage"]["cost_usd"] == r.json()["usage"]["cost_usd"] and turns[0]["created_at"]


def test_history_is_oldest_first_and_filterable_by_match(client):
    app.dependency_overrides[get_provider] = lambda: ScriptedProvider([submit(answer())] * 3)
    ask(client, "first question", match=MATCH)
    ask(client, "second question", match=3857284)
    ask(client, "third question", match=MATCH)
    assert [t["question"] for t in history(client)] == ["first question", "second question", "third question"]
    assert [t["question"] for t in history(client, match_id=MATCH)] == ["first question", "third question"]


def test_visitors_cannot_see_each_others_history_and_no_id_means_no_storage(client):
    ask(client, visitor=A)
    assert history(client, visitor=B) == [] and history(client, visitor=None) == []
    app.dependency_overrides[get_provider] = scripted
    assert ask(client, visitor=None).status_code == 200  # still answers, just does not store
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(ChatTurn).where(ChatTurn.visitor_id.like("test-visitor-%"))) == 1


def test_clear_deletes_only_the_callers_turns_and_can_be_scoped_to_a_match(client):
    app.dependency_overrides[get_provider] = lambda: ScriptedProvider([submit(answer())] * 4)
    ask(client, "alpha question", visitor=A, match=MATCH)
    ask(client, "alpha second", visitor=A, match=3857284)
    ask(client, "bravo question", visitor=B)
    h = {"X-Visitor-Id": A}
    assert client.delete("/api/v1/analyst/history", params={"match_id": MATCH}, headers=h).json() == {"deleted": 1}
    assert [t["question"] for t in history(client, visitor=A)] == ["alpha second"]
    assert client.delete("/api/v1/analyst/history", headers=h).json() == {"deleted": 1}
    assert history(client, visitor=A) == [] and len(history(client, visitor=B)) == 1
    assert client.delete("/api/v1/analyst/history").json() == {"deleted": 0}


def test_history_is_capped_per_visitor(client, monkeypatch):
    monkeypatch.setattr(routes, "MAX_TURNS_PER_VISITOR", 3)
    app.dependency_overrides[get_provider] = lambda: ScriptedProvider([submit(answer())] * 5)
    for i in range(5):
        ask(client, f"question number {i}")
    ask(client, "someone else's", visitor=B)
    assert [t["question"] for t in history(client)] == ["question number 2", "question number 3", "question number 4"]
    assert len(history(client, visitor=B)) == 1  # the cap is per visitor


def test_failed_questions_are_not_saved(client):
    class Down:
        model = "gpt-5.6-luna"

        def chat(self, *a):
            from app.agents.llm import LLMError
            raise LLMError("boom")

    app.dependency_overrides[get_provider] = lambda: Down()
    assert ask(client).status_code == 502
    assert history(client) == []


@pytest.mark.parametrize("bad", ["short", "has space in it", "x" * 65, "semi;colon-id"])
def test_a_malformed_visitor_id_is_rejected(client, bad):
    assert client.get("/api/v1/analyst/history", headers={"X-Visitor-Id": bad}).status_code == 422
    assert ask(client, visitor=bad).status_code == 422


def test_cors_allows_the_visitor_header_and_delete(client):
    r = client.options("/api/v1/analyst/history", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "DELETE", "Access-Control-Request-Headers": "x-visitor-id,content-type"})
    assert r.status_code == 200 and "DELETE" in r.headers["access-control-allow-methods"] and "x-visitor-id" in r.headers["access-control-allow-headers"].lower()


def test_hosted_database_urls_get_the_driver_and_cors_regex_is_optional():
    for given in ("postgres://u:p@host:5432/db", "postgresql://u:p@host/db?sslmode=require"):
        assert Settings(database_url=given).database_url.startswith("postgresql+psycopg://u:p@host")
    assert Settings(database_url="postgresql+psycopg://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"  # already right
    assert Settings(cors_origin_regex="https://app-.*[.]vercel[.]app").cors_origin_regex.startswith("https://app-")
