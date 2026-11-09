"""Thin LLM layer: one request/response shape for the analyst loop, and two real providers (OpenAI, Anthropic).

Internally the conversation uses Anthropic-style content blocks (assistant: text / tool_use blocks; user: a string or
tool_result blocks). Each provider translates to and from its own API inside `chat`, so the loop in analyst.py never
changes. ponytail: adding a third provider means one more class with the same `chat` method."""

import json
import os
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"
DEFAULT_MODELS = {"openai": "gpt-5.6-luna", "anthropic": "claude-opus-5-5"}
KEY_ENV = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


@dataclass(frozen=True)
class Price:
    """USD per million tokens. `cached` is the rate for input served from the prompt cache."""

    input: float
    cached: float
    output: float
    cache_write: float | None = None  # None = billed as normal input (OpenAI caches automatically at no extra charge)


# From each vendor's published pricing (OpenAI: developers.openai.com/api/docs/pricing). Update when prices change.
PRICES = {
    "gpt-5.6-luna": Price(0.20, 0.02, 1.20),  # default: current cost-sensitive tier
    "gpt-5.6-terra": Price(2.00, 0.20, 12.00),  # quality upgrade: ~10x the price
    "gpt-5.4-nano": Price(0.20, 0.02, 1.25),
    "gpt-5.4-mini": Price(0.75, 0.075, 4.50),
    "gpt-5-nano": Price(0.05, 0.005, 0.40),
    "gpt-5-mini": Price(0.25, 0.025, 2.00),  # deprecated by OpenAI, still priced for comparisons
    "gpt-4.1-mini": Price(0.40, 0.10, 1.60),
    "gpt-4o-mini": Price(0.15, 0.075, 0.60),
    "claude-opus-5-5": Price(4.0, 0.4, 20.0, cache_write=5.0),
    "claude-opus-5": Price(5.0, 0.5, 25.0, cache_write=6.25),
    "claude-sonnet-5-5": Price(2.0, 0.2, 10.0, cache_write=2.5),
    "claude-sonnet-5": Price(2.0, 0.2, 10.0, cache_write=2.5),
    "claude-haiku-5-5": Price(0.10, 0.01, 0.50, cache_write=0.125),
    "claude-fable-5-1": Price(10.0, 1.0, 50.0, cache_write=12.5),
}


class LLMError(Exception):
    """The language model call failed (network, rate limit, server error)."""


class AnalystUnavailable(LLMError):
    """No usable credentials or provider is not supported."""


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    content: list  # assistant content blocks, appended to the conversation unchanged (Anthropic: thinking blocks included)
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str  # tool_use | end_turn | max_tokens | refusal
    input_tokens: int = 0  # uncached input
    output_tokens: int = 0  # includes reasoning tokens (billed as output)
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class LLMProvider(Protocol):
    model: str

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


def cost_usd(model: str, usage: dict) -> float | None:
    """Estimated cost from token usage, or None for a model that is not in the price table."""
    p = PRICES.get(model)
    if p is None:
        return None
    write_rate = p.cache_write if p.cache_write is not None else p.input
    total = usage["input"] * p.input + usage["cache_read"] * p.cached + usage["cache_write"] * write_rate + usage["output"] * p.output
    return round(total / 1_000_000, 5)


def resolved_model() -> str:
    return settings.llm_model or DEFAULT_MODELS.get(settings.llm_provider.lower(), "")


def resolve_api_key() -> str | None:
    return settings.llm_api_key or os.environ.get(KEY_ENV.get(settings.llm_provider.lower(), ""))


# ---------------------------------------------------------------- OpenAI
def _openai_messages(system: str, messages: list[dict]) -> list[dict]:
    """Anthropic-style blocks -> Chat Completions messages. Tool results become one `tool` message per call id."""
    out: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        c = m["content"]
        if m["role"] == "user":
            if isinstance(c, str):
                out.append({"role": "user", "content": c})
                continue
            for b in c:
                if b["type"] == "tool_result":
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]})
                elif b["type"] == "text":
                    out.append({"role": "user", "content": b["text"]})
        else:
            text = "".join(b["text"] for b in c if b["type"] == "text")
            calls = [
                {"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                for b in c if b["type"] == "tool_use"
            ]
            msg: dict = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
    return out


def _reasoning_model(model: str) -> bool:
    return model.startswith(("gpt-5", "o1", "o3", "o4"))  # only these accept `reasoning_effort`


class OpenAIProvider:
    """Chat Completions with function calling. Newer models reject reasoning together with function tools on this
    endpoint (verified against the live API), so the default effort is "none". ponytail: the Responses API supports
    reasoning with tools and carries it across turns; measure with the eval before paying for that complexity."""

    def __init__(self, api_key: str | None, model: str, effort: str = "medium", client=None):
        import openai  # imported here: the SDK is slow to import and unused when another provider is configured

        self._sdk = openai
        self.model, self.effort = model, effort
        try:
            self.client = client or openai.OpenAI(api_key=api_key, timeout=120.0)  # SDK retries 429/5xx twice
        except openai.OpenAIError as e:
            raise AnalystUnavailable(f"No OpenAI credentials: {e}") from e

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        kwargs = dict(
            model=self.model,
            messages=_openai_messages(system, messages),
            tools=[{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}} for t in tools],
            max_completion_tokens=16000,  # includes reasoning tokens
        )
        if self.effort and _reasoning_model(self.model):
            kwargs["reasoning_effort"] = self.effort
        try:
            try:
                resp = self.client.chat.completions.create(**kwargs)
            except self._sdk.BadRequestError as e:
                # e.g. "Function tools with reasoning_effort are not supported for gpt-5.6-luna in /v1/chat/completions":
                # reasoning plus tools needs the Responses API, so fall back to no reasoning and remember it.
                if "reasoning_effort" not in str(e) or kwargs.get("reasoning_effort") == "none":
                    raise
                self.effort = kwargs["reasoning_effort"] = "none"
                resp = self.client.chat.completions.create(**kwargs)
        except self._sdk.AuthenticationError as e:
            raise AnalystUnavailable("The OpenAI API key was rejected") from e
        except self._sdk.OpenAIError as e:
            raise LLMError(f"{type(e).__name__}: {e}") from e

        choice = resp.choices[0]
        msg = choice.message
        calls, blocks = [], []
        if msg.content:
            blocks.append({"type": "text", "text": msg.content})
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
                if not isinstance(args, dict):
                    raise ValueError
            except ValueError:  # malformed arguments: surface them as an invalid call the loop reports back to the model
                args = {"_invalid_json": (tc.function.arguments or "")[:200]}
            calls.append(ToolCall(tc.id, tc.function.name, args))
            blocks.append({"type": "tool_use", "id": tc.id, "name": tc.function.name, "input": args})
        if getattr(msg, "refusal", None) or choice.finish_reason == "content_filter":
            stop = "refusal"
        else:
            stop = {"tool_calls": "tool_use", "stop": "end_turn", "length": "max_tokens"}.get(choice.finish_reason, "end_turn")
        usage = resp.usage
        cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        return LLMResponse(
            content=blocks,
            text=msg.content or getattr(msg, "refusal", None) or "",
            tool_calls=calls,
            stop_reason=stop,
            input_tokens=usage.prompt_tokens - cached,
            output_tokens=usage.completion_tokens,
            cache_read_tokens=cached,
        )


# ---------------------------------------------------------------- Anthropic
class AnthropicProvider:
    def __init__(self, api_key: str | None, model: str, effort: str = "medium", refusal_fallback: bool = True, client=None):
        import anthropic  # imported here: the SDK takes ~10 s to import and is unused when another provider is configured

        self._sdk = anthropic
        self.model, self.effort, self.refusal_fallback = model, effort, refusal_fallback
        try:
            self.client = client or anthropic.Anthropic(api_key=api_key, timeout=120.0)  # SDK retries 429/5xx twice
        except anthropic.AnthropicError as e:
            raise AnalystUnavailable(f"No Anthropic credentials: {e}") from e

    def _request(self, system: str, messages: list[dict], tools: list[dict]):
        kwargs = dict(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=messages,
            tools=tools,
            cache_control={"type": "ephemeral"},  # cache the growing prefix across the tool loop
        )
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}  # thinking stays on its adaptive default
        if self.refusal_fallback:
            return self.client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
        return self.client.messages.create(**kwargs)

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        try:
            try:
                resp = self._request(system, messages, tools)
            except self._sdk.BadRequestError as e:
                if not (self.refusal_fallback and "fallback" in str(e).lower()):
                    raise
                self.refusal_fallback = False  # this deployment rejects the fallback option: carry on without it
                resp = self._request(system, messages, tools)
        except self._sdk.AuthenticationError as e:
            raise AnalystUnavailable("The Anthropic API key was rejected") from e
        except self._sdk.APIError as e:
            raise LLMError(f"{type(e).__name__}: {e}") from e

        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        usage = resp.usage
        return LLMResponse(
            content=list(resp.content),
            text="".join(b.text for b in resp.content if b.type == "text"),
            tool_calls=calls,
            stop_reason=resp.stop_reason,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )


def make_provider() -> LLMProvider:
    """The configured provider (LLM_PROVIDER), or AnalystUnavailable with a message the API turns into a clear 503."""
    name = settings.llm_provider.lower()
    if name not in DEFAULT_MODELS:
        raise AnalystUnavailable(f"Unsupported LLM_PROVIDER {settings.llm_provider!r}; use 'openai' or 'anthropic'.")
    key = resolve_api_key()
    if not key:
        raise AnalystUnavailable(f"The AI analyst is not configured: set LLM_API_KEY (or {KEY_ENV[name]}) and restart the API.")
    if name == "openai":
        return OpenAIProvider(key, resolved_model(), settings.llm_effort or "none")
    return AnthropicProvider(key, resolved_model(), settings.llm_effort or "medium", settings.llm_refusal_fallback)
