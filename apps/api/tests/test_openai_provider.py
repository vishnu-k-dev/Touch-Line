"""The OpenAI provider: request shape, message translation, response parsing, error mapping, and a full agent run
through a fake OpenAI client (no network, no key)."""

import json
from types import SimpleNamespace

import openai
import pytest

from app.agents.analyst import run_analyst, tool_schemas
from app.agents.llm import (
    AnalystUnavailable, AnthropicProvider, LLMError, OpenAIProvider, _openai_messages, cost_usd, make_provider,
    resolve_api_key, resolved_model,
)
from app.core.config import settings
from app.services import analytics


def tool_call(id_, name, args):
    return SimpleNamespace(id=id_, type="function", function=SimpleNamespace(name=name, arguments=args if isinstance(args, str) else json.dumps(args)))


def response(content=None, calls=(), finish="stop", usage=(1000, 100, 0), refusal=None):
    prompt, completion, cached = usage
    msg = SimpleNamespace(content=content, tool_calls=list(calls) or None, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=msg, finish_reason=finish)],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, prompt_tokens_details=SimpleNamespace(cached_tokens=cached)),
    )


class FakeOpenAI:
    def __init__(self, *responses, fail=None):
        self.responses, self.requests, self.fail = list(responses), [], fail
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        if self.fail:
            raise self.fail
        return self.responses.pop(0)


def provider(fake, model="gpt-5.6-luna", effort="medium"):
    return OpenAIProvider(None, model, effort, client=fake)


# ---------- request shape ----------
def test_request_shape_for_a_reasoning_model():
    fake = FakeOpenAI(response("hi"))
    provider(fake).chat("SYS", [{"role": "user", "content": "question"}], tool_schemas())
    kw = fake.requests[0]
    assert kw["model"] == "gpt-5.6-luna" and kw["reasoning_effort"] == "medium" and kw["max_completion_tokens"] >= 16000
    assert kw["messages"][0] == {"role": "system", "content": "SYS"} and kw["messages"][1] == {"role": "user", "content": "question"}
    assert "temperature" not in kw and "tool_choice" not in kw and "max_tokens" not in kw
    names = [t["function"]["name"] for t in kw["tools"]]
    assert len(names) == 9 and "submit_answer" in names and all(t["type"] == "function" for t in kw["tools"])
    assert kw["tools"][0]["function"]["parameters"]["type"] == "object"


def test_reasoning_effort_is_only_sent_to_models_that_accept_it():
    for model, sent in [("gpt-5.6-luna", True), ("gpt-5-nano", True), ("o4-mini", True), ("gpt-4.1-mini", False), ("gpt-4o-mini", False)]:
        fake = FakeOpenAI(response("x"))
        provider(fake, model).chat("S", [], [])
        assert ("reasoning_effort" in fake.requests[0]) is sent, model
    fake = FakeOpenAI(response("x"))
    provider(fake, effort="").chat("S", [], [])
    assert "reasoning_effort" not in fake.requests[0]


def test_default_effort_is_none_and_a_rejected_effort_is_retried_with_none(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_effort", "")
    assert make_provider().effort == "none"

    class Bad(openai.BadRequestError):
        def __init__(self): Exception.__init__(self, "Function tools with reasoning_effort are not supported for gpt-5.6-luna in /v1/chat/completions")

    fake = FakeOpenAI(response("ok"))
    calls = []
    real = fake._create

    def create(**kw):
        calls.append(kw.get("reasoning_effort"))
        if len(calls) == 1:
            raise Bad()
        return real(**kw)

    fake.chat.completions.create = create
    p = provider(fake, effort="medium")
    assert p.chat("S", [], []).text == "ok" and calls == ["medium", "none"] and p.effort == "none"


# ---------- message translation ----------
def test_conversation_is_translated_to_chat_completions_format():
    messages = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": [{"type": "text", "text": "looking"}, {"type": "tool_use", "id": "call_1", "name": "list_matches", "input": {"team": "Japan"}},
                                           {"type": "tool_use", "id": "call_2", "name": "get_match_summary", "input": {"match_id": 1}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": '{"call_id":"c1"}', "is_error": False},
                                      {"type": "tool_result", "tool_use_id": "call_2", "content": '{"call_id":"c2","error":"x"}', "is_error": True}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "call_3", "name": "submit_answer", "input": {}}]},
        {"role": "user", "content": "Please call submit_answer."},
    ]
    out = _openai_messages("SYS", messages)
    assert [m["role"] for m in out] == ["system", "user", "assistant", "tool", "tool", "assistant", "user"]
    assert out[2]["content"] == "looking" and [c["id"] for c in out[2]["tool_calls"]] == ["call_1", "call_2"]
    assert json.loads(out[2]["tool_calls"][0]["function"]["arguments"]) == {"team": "Japan"}
    assert out[2]["tool_calls"][0]["function"]["name"] == "list_matches"
    assert [(m["tool_call_id"], m["content"][:12]) for m in out[3:5]] == [("call_1", '{"call_id":"'), ("call_2", '{"call_id":"')]
    assert out[5]["content"] is None and out[5]["tool_calls"][0]["id"] == "call_3"  # tool-call-only turn has null content


# ---------- response parsing ----------
def test_response_parsing_and_usage_normalisation():
    fake = FakeOpenAI(response("ok", [tool_call("call_a", "list_matches", {"team": "x"})], "tool_calls", usage=(1500, 300, 1000)))
    r = provider(fake).chat("S", [], [])
    assert [(c.id, c.name, c.args) for c in r.tool_calls] == [("call_a", "list_matches", {"team": "x"})]
    assert r.stop_reason == "tool_use" and r.text == "ok"
    assert r.content == [{"type": "text", "text": "ok"}, {"type": "tool_use", "id": "call_a", "name": "list_matches", "input": {"team": "x"}}]
    assert (r.input_tokens, r.cache_read_tokens, r.output_tokens) == (500, 1000, 300)  # prompt tokens include the cached ones


def test_finish_reasons_map_to_the_loops_stop_reasons():
    assert provider(FakeOpenAI(response("a", finish="stop"))).chat("S", [], []).stop_reason == "end_turn"
    assert provider(FakeOpenAI(response("a", finish="length"))).chat("S", [], []).stop_reason == "max_tokens"
    assert provider(FakeOpenAI(response(None, finish="content_filter"))).chat("S", [], []).stop_reason == "refusal"
    r = provider(FakeOpenAI(response(None, finish="stop", refusal="I can't help with that."))).chat("S", [], [])
    assert r.stop_reason == "refusal" and "can't help" in r.text


def test_malformed_tool_arguments_become_an_invalid_call_not_a_crash():
    fake = FakeOpenAI(response(None, [tool_call("c1", "get_match_summary", '{"match_id": 38'), tool_call("c2", "list_matches", "[1]")], "tool_calls"))
    r = provider(fake).chat("S", [], [])
    assert r.tool_calls[0].args == {"_invalid_json": '{"match_id": 38'} and "_invalid_json" in r.tool_calls[1].args


# ---------- errors ----------
def test_error_mapping():
    class NoAuth(openai.AuthenticationError):
        def __init__(self): Exception.__init__(self, "bad key")

    class Down(openai.APIConnectionError):
        def __init__(self): Exception.__init__(self, "unreachable")

    with pytest.raises(AnalystUnavailable):
        provider(FakeOpenAI(fail=NoAuth())).chat("S", [], [])
    with pytest.raises(LLMError, match="unreachable"):
        provider(FakeOpenAI(fail=Down())).chat("S", [], [])


# ---------- the whole agent loop through the OpenAI translation ----------
def test_full_agent_run_through_the_openai_provider(db):
    s = analytics.match_stats(db, 3857300)
    submit = {
        "question": "Why did Argentina lose?",
        "findings": [{"claim": "Argentina had far more xG", "metric": "xG", "values": {"Argentina xG": s["home"]["xg"], "Saudi Arabia xG": s["away"]["xg"]}, "sources": ["c1"], "evidence": []}],
        "interpretation": "Finishing variance (inference).", "limitations": ["One match is a small sample."],
    }
    fake = FakeOpenAI(
        response(None, [tool_call("call_1", "get_match_summary", {"match_id": 3857300}), tool_call("call_2", "get_shot_map", {"match_id": 3857300, "team": "Argentina", "limit": 5})], "tool_calls", usage=(3000, 200, 0)),
        response(None, [tool_call("call_3", "submit_answer", submit)], "tool_calls", usage=(6000, 400, 2800)),
    )
    r = run_analyst(db, provider(fake), "Why did Argentina lose?", 3857300)
    assert r.status == "answered" and r.validation.passed and [t.tool for t in r.trace] == ["get_match_summary", "get_shot_map"]
    second = fake.requests[1]["messages"]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "tool", "tool"]
    assert [m["tool_call_id"] for m in second[3:]] == ["call_1", "call_2"]  # results line up with the model's call ids
    assert json.loads(second[3]["content"])["call_id"] == "c1" and second[2]["tool_calls"][0]["function"]["name"] == "get_match_summary"
    assert r.usage.input_tokens == 3000 + 3200 and r.usage.cache_read_tokens == 2800 and r.usage.output_tokens == 600
    assert r.usage.model == "gpt-5.6-luna" and r.usage.cost_usd == pytest.approx((6200 * 0.20 + 2800 * 0.02 + 600 * 1.20) / 1e6, abs=1e-5)


def test_a_malformed_call_is_reported_to_the_model_and_the_run_recovers(db):
    fake = FakeOpenAI(
        response(None, [tool_call("call_1", "get_match_summary", '{"match_id": 38')], "tool_calls"),
        response(None, [tool_call("call_2", "submit_answer", {"question": "q", "findings": [], "interpretation": "", "limitations": ["no data"]})], "tool_calls"),
    )
    r = run_analyst(db, provider(fake), "q")
    assert [(t.ok) for t in r.trace] == [False] and "Invalid arguments" in r.trace[0].summary and r.status == "answered"
    assert "error" in json.loads(fake.requests[1]["messages"][-1]["content"])


# ---------- factory, defaults and pricing ----------
def test_defaults_prefer_openai_and_a_cheap_current_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_model", "")
    assert resolved_model() == "gpt-5.6-luna"
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    assert resolved_model() == "claude-opus-5-5"
    monkeypatch.setattr(settings, "llm_model", "claude-sonnet-5-5")
    assert resolved_model() == "claude-sonnet-5-5"


def test_factory_builds_the_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", None)
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_model", "")
    with pytest.raises(AnalystUnavailable, match="OPENAI_API_KEY"):
        make_provider()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_api_key() == "sk-test"
    p = make_provider()
    assert isinstance(p, OpenAIProvider) and p.model == "gpt-5.6-luna"
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert isinstance(make_provider(), AnthropicProvider)
    monkeypatch.setattr(settings, "llm_provider", "mystery")
    with pytest.raises(AnalystUnavailable, match="Unsupported"):
        make_provider()
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_api_key", "from-config")
    assert resolve_api_key() == "from-config"  # LLM_API_KEY wins over the vendor variable


def test_openai_pricing():
    u = dict(input=20_000, output=3_000, cache_read=0, cache_write=0)
    assert cost_usd("gpt-5.6-luna", u) == pytest.approx(0.0076)  # about three-quarters of a cent for a typical question
    assert cost_usd("gpt-5.6-terra", u) == pytest.approx(0.076)
    assert cost_usd("gpt-5.6-luna", dict(input=0, output=0, cache_read=1_000_000, cache_write=0)) == pytest.approx(0.02)
    assert cost_usd("gpt-4o-mini", u) is not None and cost_usd("not-a-model", u) is None
    assert cost_usd("claude-opus-5-5", dict(input=0, output=0, cache_read=0, cache_write=1_000_000)) == pytest.approx(5.0)
