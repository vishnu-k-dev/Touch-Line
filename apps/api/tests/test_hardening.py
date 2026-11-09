"""Day 6: rate limits, spend cap, request tracing and readiness."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agent_helpers import ScriptedProvider, answer, submit, tool_use
from app.api.routes import get_provider
from app.core.limits import UNKNOWN_COST_USD, Limiter, get_limiter
from app.main import app


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def _blocked(limiter, client="a"):
    try:
        limiter.acquire(client)
    except HTTPException as e:
        return e
    limiter.release(0.0)
    return None


def test_per_minute_limit_blocks_then_recovers():
    clock = Clock()
    lim = Limiter(per_minute=3, per_day=100, daily_budget_usd=100, max_concurrent=5, clock=clock)
    for _ in range(3):
        assert _blocked(lim) is None
    e = _blocked(lim)
    assert e.status_code == 429 and int(e.headers["Retry-After"]) >= 1
    assert _blocked(lim, "someone-else") is None  # limits are per client
    clock.t += 61
    assert _blocked(lim) is None


def test_daily_per_client_cap_and_day_rollover():
    clock = Clock()
    lim = Limiter(per_minute=100, per_day=2, daily_budget_usd=100, max_concurrent=5, clock=clock)
    assert _blocked(lim) is None and _blocked(lim) is None
    e = _blocked(lim)
    assert e.status_code == 429 and "Daily" in e.detail
    clock.t += 86400
    assert _blocked(lim) is None


def test_daily_budget_stops_everyone_and_resets_next_day():
    clock = Clock()
    lim = Limiter(per_minute=100, per_day=100, daily_budget_usd=0.10, max_concurrent=5, clock=clock)
    lim.acquire("a")
    lim.release(0.12)  # one expensive answer exhausts the budget
    assert lim.spent_today == pytest.approx(0.12)
    e = _blocked(lim, "b")
    assert e.status_code == 503 and "budget" in e.detail
    clock.t += 86400
    assert _blocked(lim, "b") is None and lim.spent_today == 0.0


def test_unknown_cost_is_charged_conservatively_and_failed_calls_are_not_charged():
    lim = Limiter(100, 100, 100, 5)
    lim.acquire("a")
    lim.release(None)
    assert lim.spent_today == UNKNOWN_COST_USD
    lim.acquire("a")
    lim.release(None, charged=False)
    assert lim.spent_today == UNKNOWN_COST_USD


def test_concurrency_cap_releases_slots():
    lim = Limiter(100, 100, 100, max_concurrent=2)
    lim.acquire("a")
    lim.acquire("b")
    e = _blocked(lim, "c")
    assert e.status_code == 503 and "busy" in e.detail
    lim.release(0.0)
    assert _blocked(lim, "c") is None


@pytest.fixture
def client(db):
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_returns_429_with_retry_after_when_limited(client):
    lim = Limiter(per_minute=1, per_day=100, daily_budget_usd=100, max_concurrent=5)
    app.dependency_overrides[get_limiter] = lambda: lim
    app.dependency_overrides[get_provider] = lambda: ScriptedProvider([tool_use(("list_matches", {})), submit(answer())])
    body = {"question": "valid question"}
    assert client.post("/api/v1/analyst/chat", json=body).status_code == 200
    r = client.post("/api/v1/analyst/chat", json=body)
    assert r.status_code == 429 and r.headers["retry-after"] and "Too many" in r.json()["detail"]
    assert lim.spent_today > 0  # the first answer was charged its real cost


def test_failed_model_call_releases_the_slot_without_charging(client):
    class Down:
        model = "claude-opus-5-5"

        def chat(self, *a):
            from app.agents.llm import LLMError
            raise LLMError("boom")

    lim = Limiter(100, 100, 100, max_concurrent=1)
    app.dependency_overrides[get_limiter] = lambda: lim
    app.dependency_overrides[get_provider] = lambda: Down()
    assert client.post("/api/v1/analyst/chat", json={"question": "valid question"}).status_code == 502
    assert client.post("/api/v1/analyst/chat", json={"question": "valid question"}).status_code == 502  # slot was freed
    assert lim.spent_today == 0.0


def test_every_response_carries_a_request_id(client):
    r = client.get("/api/v1/matches")
    assert len(r.headers["x-request-id"]) == 12
    assert client.get("/health", headers={"X-Request-ID": "trace-me"}).headers["x-request-id"] == "trace-me"


def test_cors_allows_the_web_origin_and_exposes_headers(client):
    r = client.get("/api/v1/matches", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in client.get("/api/v1/matches", headers={"Origin": "https://evil.example"}).headers


def test_unhandled_error_becomes_a_clean_500_with_request_id(client):
    @app.get("/boom-test")
    def boom():
        raise RuntimeError("secret internal detail")

    try:
        r = TestClient(app, raise_server_exceptions=False).get("/boom-test")
    finally:
        app.router.routes.pop()  # drop the temporary route so other tests see the real app
    assert r.status_code == 500 and r.json()["detail"] == "Internal server error" and r.json()["request_id"]
    assert "secret" not in r.text


def test_readiness_reports_data_and_index(client):
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json() == {**r.json(), "status": "ready", "matches": 5, "problems": []} and r.json()["documents"] > 100
    assert client.get("/health").json()["status"] == "healthy"
