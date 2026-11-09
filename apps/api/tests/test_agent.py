"""Day 4: the analyst loop, evidence validator, tools and API, with a scripted model (no network, no API key)."""

import pytest
from fastapi.testclient import TestClient

from agent_helpers import ScriptedProvider, answer, finding, refusal, results_of, say, submit, tool_use
from app.agents import analyst
from app.agents.analyst import Answer, CallRecord, run_analyst, tool_schemas, validate_answer
from app.agents.llm import AnalystUnavailable, AnthropicProvider, LLMResponse, cost_usd
from app.api.routes import get_provider
from app.core.config import settings
from app.core.limits import Limiter, get_limiter
from app.main import app
from app.services import analytics
from app.tools import football as ft

SAUDI = 3857300  # Argentina 1-2 Saudi Arabia
FINAL = 3869685


# ---------- the loop ----------
def _happy_steps(db):
    s = analytics.match_stats(db, SAUDI)

    def final(messages):
        res = results_of(messages)
        ev = [x["event_id"] for x in res["c2"]["shots"][:2]]
        return submit(answer(
            "Why did Argentina lose?",
            [finding("Argentina had far more xG", "xG", {"Argentina xG": s["home"]["xg"], "Saudi Arabia xG": s["away"]["xg"], "gap": round(s["home"]["xg"] - s["away"]["xg"], 2), "Argentina shots": s["home"]["shots"]},
                     ["c1"], []),
             finding("Two of Argentina's shots", "shots", {}, ["c2"], ev)],
            "Probably finishing variance.", ["One match is a small sample."]))

    return [tool_use(("get_match_summary", {"match_id": SAUDI}), ("get_shot_map", {"match_id": SAUDI, "team": "Argentina"})), final]


def test_happy_path_answer_is_verified(db):
    p = ScriptedProvider(_happy_steps(db))
    r = run_analyst(db, p, "Why did Argentina lose?", SAUDI)
    assert r.status == "answered" and r.validation.passed and r.validation.violations == []
    assert [t.tool for t in r.trace] == ["get_match_summary", "get_shot_map"] and all(t.ok for t in r.trace)
    assert all(f.verified for f in r.answer.findings)
    assert r.usage.steps == 2 and r.usage.tool_calls == 2 and r.usage.input_tokens == 2000
    assert r.usage.cost_usd == pytest.approx(cost_usd("claude-opus-5-5", dict(input=2000, output=200, cache_read=0, cache_write=0)))
    assert "match_id 3857300" in p.requests[0][0]["content"]  # the UI's match context reaches the model


def test_fabricated_number_is_sent_back_then_accepted_once_fixed(db):
    s = analytics.match_stats(db, SAUDI)
    bad = submit(answer(findings=[finding("x", "xG", {"Argentina xG": 3.5}, ["c1"])]))
    good = submit(answer(findings=[finding("x", "xG", {"Argentina xG": s["home"]["xg"]}, ["c1"])]))
    p = ScriptedProvider([tool_use(("get_match_summary", {"match_id": SAUDI})), bad, good])
    r = run_analyst(db, p, "q")
    feedback = results_of(p.requests[2])
    assert any("does not appear in the cited tool results" in v["error"] for v in feedback.values())
    assert r.status == "answered" and r.validation.passed and r.usage.steps == 3


def test_uncorrected_fabrication_is_returned_flagged_never_silently_accepted(db):
    bad = submit(answer(findings=[finding("x", "xG", {"Argentina xG": 9.9}, ["c1"], ["not-a-real-event-id"])]))
    r = run_analyst(db, ScriptedProvider([tool_use(("get_match_summary", {"match_id": SAUDI})), bad, bad]), "q")
    assert r.status == "unverified" and not r.validation.passed
    f = r.answer.findings[0]
    assert not f.verified and len(f.problems) == 2 and "9.9" in f.problems[0] and "not-a-real-event-id" in f.problems[1]


def test_source_must_be_a_real_successful_call(db):
    bad = submit(answer(findings=[finding("x", "xG", {"a": 1}, ["c9"])]))
    r = run_analyst(db, ScriptedProvider([tool_use(("list_matches", {})), bad, bad]), "q")
    assert r.status == "unverified" and "unknown or failed source" in r.validation.violations[0]


def test_tool_errors_are_fed_back_and_the_loop_recovers(db):
    steps = [
        tool_use(("get_match_summary", {"match_id": 1})),
        lambda m: (tool_use(("list_matches", {})) if results_of(m)["c1"]["_is_error"] else say("?")),
        submit(answer(limitations=["asked about an unknown match"])),
    ]
    r = run_analyst(db, ScriptedProvider(steps), "q")
    assert [(t.tool, t.ok) for t in r.trace] == [("get_match_summary", False), ("list_matches", True)]
    assert "No match with id 1" in r.trace[0].summary and r.status == "answered"


def test_unknown_tool_bad_arguments_and_extra_arguments(db):
    steps = [
        tool_use(("fly_to_moon", {}), ("get_shot_map", {"match_id": "abc"}), ("get_match_summary", {"match_id": SAUDI, "nonsense": 1})),
        submit(answer()),
    ]
    p = ScriptedProvider(steps)
    r = run_analyst(db, p, "q")
    assert [t.ok for t in r.trace] == [False, False, False]
    errors = [v["error"] for v in results_of(p.requests[1]).values()]
    assert "Unknown tool" in errors[0] and "Invalid arguments" in errors[1] and "Invalid arguments" in errors[2]


def test_prose_instead_of_structured_answer_gets_one_nudge(db):
    p = ScriptedProvider([say("It was variance."), submit(answer(limitations=["x"]))])
    assert run_analyst(db, p, "q").status == "answered"
    assert "submit_answer" in p.requests[1][-1]["content"]
    r = run_analyst(db, ScriptedProvider([say("a"), say("b")]), "q")
    assert r.status == "incomplete" and r.answer is None


def test_invalid_answer_schema_is_rejected_with_a_message(db):
    p = ScriptedProvider([submit({"question": "q"}), submit(answer())])
    r = run_analyst(db, p, "q")
    assert "Invalid answer" in results_of(p.requests[1])["toolu_0_submit_answer"]["error"] and r.status == "answered"


def test_step_limit_and_refusal(db):
    r = run_analyst(db, ScriptedProvider([tool_use(("list_matches", {}))] * 3), "q", max_steps=3)
    assert r.status == "incomplete" and r.usage.steps == 3 and r.answer is None and not r.validation.passed
    r = run_analyst(db, ScriptedProvider([refusal()]), "q")
    assert r.status == "refused" and "can't help" in r.message


def test_derived_values_are_checked_against_sources_not_waved_through(db):
    s = analytics.match_stats(db, SAUDI)
    gap = round(s["home"]["xg"] - s["away"]["xg"], 2)
    ok = submit(answer(findings=[finding("gap", "xG gap", {"gap": gap, "total shots": s["home"]["shots"] + s["away"]["shots"]}, ["c1"])]))
    assert run_analyst(db, ScriptedProvider([tool_use(("get_match_summary", {"match_id": SAUDI})), ok]), "q").status == "answered"
    wrong = submit(answer(findings=[finding("gap", "xG gap", {"gap": gap + 0.5}, ["c1"])]))
    r = run_analyst(db, ScriptedProvider([tool_use(("get_match_summary", {"match_id": SAUDI})), wrong, wrong]), "q")
    assert r.status == "unverified"


def test_validate_answer_unit():
    calls = {"c1": CallRecord("c1", "t", True, {"e1"}, [2.49, 0.15, 15.0]), "c2": CallRecord("c2", "t", False)}
    a = Answer(question="q", findings=[
        {"claim": "ok", "metric": "m", "values": {"a": 2.49, "b": 15, "name": "Argentina"}, "sources": ["c1"], "evidence": ["e1"]},
        {"claim": "bad", "metric": "m", "values": {"a": 2.5 + 1}, "sources": ["c1"], "evidence": ["zzz"]},
        {"claim": "failed source", "metric": "m", "values": {}, "sources": ["c2"]},
    ], interpretation="", limitations=[])
    findings, violations = validate_answer(a, calls)
    assert [f.verified for f in findings] == [True, False, False] and len(violations) == 3


def test_tool_schemas_are_well_formed():
    schemas = tool_schemas()
    names = [s["name"] for s in schemas]
    assert names == list(ft.TOOLS) + ["submit_answer"] and len(set(names)) == 9
    for s in schemas:
        assert s["description"] and s["input_schema"]["type"] == "object"


# ---------- the tools ----------
def test_tools_return_what_analytics_returns(db):
    assert len(ft.list_matches(db, ft.ListMatchesArgs())["matches"]) == 5
    assert [m["match_id"] for m in ft.list_matches(db, ft.ListMatchesArgs(team="japan"))["matches"]] == [3857284]
    assert ft.get_match_summary(db, ft.MatchArgs(match_id=SAUDI))["home"]["xg"] == analytics.match_stats(db, SAUDI)["home"]["xg"]
    p = ft.calculate_ppda(db, ft.MatchArgs(match_id=3869220))
    assert [t["team"] for t in p["teams"]] == ["Morocco", "Spain"] and p["teams"][0]["ppda"] > p["teams"][1]["ppda"]


def test_shot_map_filters_and_truncation(db):
    goals = ft.get_shot_map(db, ft.ShotMapArgs(match_id=FINAL, outcome="goal"))
    assert goals["total_matching"] == 6 and {s["outcome"] for s in goals["shots"]} == {"Goal"}
    arg = ft.get_shot_map(db, ft.ShotMapArgs(match_id=FINAL, team="argentina"))
    assert arg["total_matching"] == 20 and {s["team"] for s in arg["shots"]} == {"Argentina"}
    small = ft.get_shot_map(db, ft.ShotMapArgs(match_id=FINAL, limit=5))
    assert small["truncated"] and len(small["shots"]) == 5 and small["total_matching"] == 30
    assert ft.get_shot_map(db, ft.ShotMapArgs(match_id=FINAL, include_shootout=True))["total_matching"] == 38


def test_player_lookup_is_accent_insensitive_and_reports_ambiguity(db):
    mb = ft.get_player_stats(db, ft.PlayerStatsArgs(match_id=FINAL, player="mbappe"))
    assert mb["total_matching"] == 1 and mb["players"][0]["goals"] == 3 and mb["players"][0]["minutes"] > 100
    cmp = ft.compare_players(db, ft.ComparePlayersArgs(match_id=FINAL, player_a="Messi", player_b="Mbappe"))
    assert (cmp["player_a"]["goals"], cmp["player_b"]["goals"]) == (2, 3)
    with pytest.raises(ft.ToolError, match="No player"):
        ft.compare_players(db, ft.ComparePlayersArgs(match_id=FINAL, player_a="Messi", player_b="Nobody"))
    with pytest.raises(ft.ToolError, match="several players"):
        ft.compare_players(db, ft.ComparePlayersArgs(match_id=FINAL, player_a="Messi", player_b="a"))
    with pytest.raises(ft.ToolError, match="same player"):
        ft.compare_players(db, ft.ComparePlayersArgs(match_id=FINAL, player_a="Messi", player_b="messi"))


def test_team_events(db):
    counts = ft.get_team_events(db, ft.TeamEventsArgs(match_id=FINAL, team="France"))["event_counts"]
    assert counts["Pass"] == analytics.match_stats(db, FINAL)["away"]["passes"]
    ev = ft.get_team_events(db, ft.TeamEventsArgs(match_id=FINAL, team="France", event_type="foul committed", limit=3))
    assert ev["total"] == analytics.match_stats(db, FINAL)["away"]["fouls_committed"] and len(ev["events"]) == 3 and ev["events"][0]["event_id"]
    with pytest.raises(ft.ToolError, match="Available types"):
        ft.get_team_events(db, ft.TeamEventsArgs(match_id=FINAL, team="France", event_type="Teleport"))
    with pytest.raises(ft.ToolError, match="not \\(uniquely\\) in this match"):
        ft.get_team_events(db, ft.TeamEventsArgs(match_id=FINAL, team="Brazil"))


def test_knowledge_tool(db, indexed):
    r = ft.search_tactical_knowledge(db, ft.KnowledgeArgs(query="how is pressing measured", kind="knowledge", k=2))["results"]
    assert len(r) == 2 and all(h["kind"] == "knowledge" for h in r)
    seq = ft.search_tactical_knowledge(db, ft.KnowledgeArgs(query="chance", play_pattern="From Corner", body_part="Head", k=3))["results"]
    assert seq and all(h["kind"] == "sequence" and h["event_ids"] for h in seq)
    with pytest.raises(ft.ToolError, match="only apply to kind='sequence'"):
        ft.search_tactical_knowledge(db, ft.KnowledgeArgs(query="chance", kind="knowledge", outcome="Goal"))


def test_collect_gathers_event_ids_and_numbers():
    events, numbers = ft.collect({"shots": [{"event_id": "a", "xg": 0.5}, {"event_id": "b", "xg": 0.25}], "x": {"event_ids": ["c"], "n": True}})
    assert events == {"a", "b", "c"} and sorted(numbers) == [0.25, 0.5, 2.0]  # 2.0 = length of the shots list; bool ignored


# ---------- the API ----------
@pytest.fixture
def client(db):
    app.dependency_overrides[get_limiter] = lambda: Limiter(1000, 1000, 1e9, 10)  # these tests are not about limits
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_returns_503_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post("/api/v1/analyst/chat", json={"question": "why did Argentina lose?"})
    assert r.status_code == 503 and "not configured" in r.json()["detail"] and "OPENAI_API_KEY" in r.json()["detail"]
    assert client.get("/api/v1/analyst/status").json() == {"configured": False, "provider": "openai", "model": "gpt-5.6-luna"}


def test_chat_endpoint_with_scripted_model(client, db):
    app.dependency_overrides[get_provider] = lambda: ScriptedProvider(_happy_steps(db))
    r = client.post("/api/v1/analyst/chat", json={"question": "Why did Argentina lose?", "match_id": SAUDI})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "answered" and body["validation"]["passed"]
    assert body["answer"]["findings"][0]["verified"] and [t["tool"] for t in body["trace"]] == ["get_match_summary", "get_shot_map"]
    assert body["usage"]["cost_usd"] > 0


def test_chat_input_validation(client, monkeypatch):
    app.dependency_overrides[get_provider] = lambda: ScriptedProvider([])
    assert client.post("/api/v1/analyst/chat", json={"question": "hi"}).status_code == 422
    assert client.post("/api/v1/analyst/chat", json={"question": "x" * 501}).status_code == 422
    assert client.post("/api/v1/analyst/chat", json={"question": "valid question", "match_id": 1}).status_code == 404


def test_llm_failure_becomes_502(client):
    class Down:
        model = "claude-opus-5-5"

        def chat(self, *a):
            from app.agents.llm import LLMError
            raise LLMError("APIConnectionError: boom")

    app.dependency_overrides[get_provider] = lambda: Down()
    r = client.post("/api/v1/analyst/chat", json={"question": "valid question"})
    assert r.status_code == 502 and "boom" in r.json()["detail"]


# ---------- the Anthropic provider (mocked client) ----------
class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _fake_response(blocks, stop="tool_use"):
    usage = _Block(input_tokens=1200, output_tokens=80, cache_read_input_tokens=1000, cache_creation_input_tokens=0)
    return _Block(content=blocks, stop_reason=stop, usage=usage)


class FakeClient:
    def __init__(self, response=None, fail_first=None):
        self.calls, self.response, self.fail_first = [], response, fail_first
        client = self
        class _M:
            def __init__(self, beta): self.beta = beta
            def create(self, **kw):
                client.calls.append(("beta" if self.beta else "plain", kw))
                if client.fail_first and len(client.calls) == 1:
                    raise client.fail_first
                return client.response
        self.messages = _M(False)
        self.beta = _Block(messages=_M(True))


def test_provider_request_shape_and_parsing():
    blocks = [_Block(type="thinking", thinking=""), _Block(type="text", text="ok"),
              _Block(type="tool_use", id="toolu_1", name="list_matches", input={"team": "Japan"})]
    fake = FakeClient(_fake_response(blocks))
    p = AnthropicProvider(None, "claude-opus-5-5", "medium", True, client=fake)
    r = p.chat("SYS", [{"role": "user", "content": "hi"}], tool_schemas())
    kind, kw = fake.calls[0]
    assert kind == "beta" and kw["betas"] == ["server-side-fallback-2026-07-01"] and kw["fallbacks"] == "default"
    assert kw["model"] == "claude-opus-5-5" and kw["system"] == "SYS" and kw["output_config"] == {"effort": "medium"}
    assert kw["max_tokens"] >= 16000 and len(kw["tools"]) == 9
    assert "thinking" not in kw and "tool_choice" not in kw and "temperature" not in kw  # adaptive default; forced tool use is rejected on this model
    assert [(c.id, c.name, c.args) for c in r.tool_calls] == [("toolu_1", "list_matches", {"team": "Japan"})]
    assert r.text == "ok" and len(r.content) == 3 and r.content[0].type == "thinking"  # thinking block kept for replay
    assert (r.input_tokens, r.output_tokens, r.cache_read_tokens, r.stop_reason) == (1200, 80, 1000, "tool_use")


def test_provider_without_fallback_uses_plain_endpoint_and_optional_effort():
    fake = FakeClient(_fake_response([_Block(type="text", text="x")], "end_turn"))
    AnthropicProvider(None, "claude-sonnet-5-5", "", False, client=fake).chat("S", [], [])
    kind, kw = fake.calls[0]
    assert kind == "plain" and "output_config" not in kw and "betas" not in kw


def test_provider_retries_without_fallback_if_the_deployment_rejects_it_and_maps_auth_errors():
    import anthropic  # local: the SDK is slow to import

    class Bad(anthropic.BadRequestError):
        def __init__(self, msg): Exception.__init__(self, msg)

    class NoAuth(anthropic.AuthenticationError):
        def __init__(self): Exception.__init__(self, "bad key")

    fake = FakeClient(_fake_response([_Block(type="text", text="x")], "end_turn"), fail_first=Bad("unknown field: fallbacks"))
    p = AnthropicProvider(None, "claude-opus-5-5", "medium", True, client=fake)
    assert p.chat("S", [], []).text == "x" and [k for k, _ in fake.calls] == ["beta", "plain"] and p.refusal_fallback is False
    with pytest.raises(AnalystUnavailable):
        AnthropicProvider(None, "m", client=FakeClient(fail_first=NoAuth())).chat("S", [], [])


def test_cost_accounting():
    assert cost_usd("claude-opus-5-5", dict(input=1000, output=500, cache_read=0, cache_write=0)) == pytest.approx(0.014)
    assert cost_usd("claude-opus-5-5", dict(input=0, output=0, cache_read=10_000, cache_write=0)) == pytest.approx(0.004)
    assert cost_usd("some-future-model", dict(input=1, output=1, cache_read=0, cache_write=0)) is None
