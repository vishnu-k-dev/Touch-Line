"""A scripted stand-in for the LLM so the agent loop, validator and API can be tested offline and deterministically."""

import json

from app.agents.llm import LLMResponse, ToolCall


class ScriptedProvider:
    model = "claude-opus-5-5"  # a priced model, so cost accounting is exercised too

    def __init__(self, steps):
        self.steps = list(steps)
        self.requests = []  # copy of the messages the loop sent at each step

    def chat(self, system, messages, tools):
        self.requests.append(list(messages))
        step = self.steps.pop(0)
        return step(messages) if callable(step) else step


def tool_use(*calls, usage=(1000, 100)):
    tcs = [ToolCall(f"toolu_{i}_{name}", name, args) for i, (name, args) in enumerate(calls)]
    content = [{"type": "tool_use", "id": t.id, "name": t.name, "input": t.args} for t in tcs]
    return LLMResponse(content, "", tcs, "tool_use", *usage)


def say(text):
    return LLMResponse([{"type": "text", "text": text}], text, [], "end_turn", 50, 20)


def refusal():
    return LLMResponse([], "I can't help with that.", [], "refusal", 50, 5)


def results_of(messages):
    """Parsed tool results from the latest user message: {call_id: body}."""
    out = {}
    for block in messages[-1]["content"]:
        body = json.loads(block["content"]) if block["content"].startswith("{") else {"error": block["content"]}
        out[body.get("call_id", block["tool_use_id"])] = {**body, "_is_error": block.get("is_error", False)}
    return out


def submit(answer):
    return tool_use(("submit_answer", answer))


def answer(question="q", findings=(), interpretation="", limitations=()):
    return {"question": question, "findings": list(findings), "interpretation": interpretation, "limitations": list(limitations)}


def finding(claim, metric, values, sources, evidence=()):
    return {"claim": claim, "metric": metric, "values": values, "sources": list(sources), "evidence": list(evidence)}
