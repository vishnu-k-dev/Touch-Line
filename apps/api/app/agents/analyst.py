"""The analyst agent: a controlled tool-calling loop with an evidence validator.

Custom orchestration (no framework): the loop is ~60 lines, every step is visible in `trace`, and the control flow
that matters (step limit, argument validation, error feedback, the final-answer check) is explicit code.

Contract with the model: call tools to get facts, then call `submit_answer` once. Each finding must cite the tool
calls (`call_id`) that contain its numbers and the event ids that back it. `validate_answer` checks those citations
against what the tools actually returned; a failed check is sent back to the model once for correction, and anything
still unverified is returned flagged, never silently accepted."""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.agents.llm import LLMProvider, cost_usd
from app.core.config import settings
from app.tools.football import TOOLS, ToolError, collect

logger = logging.getLogger("touchline.agent")

SUBMIT = "submit_answer"
MAX_RESULT_CHARS = 20_000
TOLERANCE = 0.0051  # a number matches if it equals a source number to two decimals

SYSTEM = """You are Touchline AI, a football tactical analyst. You answer questions about matches in a database of StatsBomb event data (a FIFA World Cup 2022 sample).

Rules:
1. Every number you state must come from a tool result in this conversation. Never use memory for match facts or statistics; if you need a number, call a tool.
2. If no match_id is given, identify the match first with list_matches.
3. Keep measured facts apart from interpretation. Findings are measured facts: each cites the call_id values of the tool results holding its numbers and, where the tools returned them, the event ids behind it. Your interpretation is inference and may be wrong: say what would support or contradict it.
4. Be economical. Typically: match summary, shot map, then one or two targeted checks. Do not call tools whose results you will not use.
5. xG and counts exclude penalty-shootout kicks. A single match is a small sample; say so when it matters.
6. The data has no tracking: you cannot state formations, off-ball runs or player speed. defenders_in_cone is a lower bound on visible defenders and only meaningful when cone_visible is true. If a question needs data you do not have, say so under limitations instead of guessing, and make no finding about it.
7. When you have what you need, call submit_answer exactly once. Do not write the final answer as plain text."""


class Finding(BaseModel):
    claim: str = Field(description="One measured fact, stated plainly.")
    metric: str = Field(description="Metric name, e.g. xG, shots, PPDA, minutes.")
    values: dict[str, float | int | str] = Field(
        description="The numbers behind the claim keyed by label, e.g. {\"Argentina xG\": 2.49}. Every number must appear in a cited tool result (differences and sums of two such numbers are allowed)."
    )
    sources: list[str] = Field(min_length=1, description="call_id values of the tool results holding these numbers, e.g. [\"c1\"].")
    evidence: list[str] = Field(default_factory=list, description="StatsBomb event ids returned by tools that back the claim.")


class Answer(BaseModel):
    question: str
    findings: list[Finding] = Field(description="Measured facts only. Empty if the data cannot answer the question.")
    interpretation: str = Field(description="Your inference about why, with its uncertainty. Empty for purely factual questions.")
    limitations: list[str] = Field(description="What the data cannot show or what to be careful about.")


class FindingOut(Finding):
    verified: bool = True
    problems: list[str] = []


class AnswerOut(BaseModel):
    question: str
    findings: list[FindingOut]
    interpretation: str
    limitations: list[str]


class TraceStep(BaseModel):
    step: int
    tool: str
    call_id: str
    args: dict
    ok: bool
    ms: int
    summary: str


class Validation(BaseModel):
    passed: bool
    violations: list[str] = []


class Usage(BaseModel):
    model: str
    steps: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: float | None
    latency_ms: int


class AnalystResult(BaseModel):
    status: Literal["answered", "unverified", "incomplete", "refused"]
    answer: AnswerOut | None
    message: str | None = None
    validation: Validation
    trace: list[TraceStep]
    usage: Usage


@dataclass
class CallRecord:
    id: str
    name: str
    ok: bool
    event_ids: set = field(default_factory=set)
    numbers: list = field(default_factory=list)


def tool_schemas() -> list[dict]:
    tools = [{"name": t.name, "description": t.description, "input_schema": t.args.model_json_schema()} for t in TOOLS.values()]
    tools.append({
        "name": SUBMIT,
        "description": "Submit the final structured answer. Call exactly once, after gathering facts with the other tools.",
        "input_schema": Answer.model_json_schema(),
    })
    return tools


def _supported(value: float, numbers: list[float]) -> bool:
    """True if `value` equals a source number, or the difference or sum of two (rounded to two decimals)."""
    uniq = sorted({round(n, 4) for n in numbers})[:400]
    if any(abs(value - n) <= TOLERANCE for n in uniq):
        return True
    return any(abs(value - (a + b)) <= TOLERANCE or abs(value - abs(a - b)) <= TOLERANCE for a in uniq for b in uniq)


def validate_answer(answer: Answer, calls: dict[str, CallRecord]) -> tuple[list[FindingOut], list[str]]:
    seen_events = set().union(*(c.event_ids for c in calls.values())) if calls else set()
    findings, violations = [], []
    for i, f in enumerate(answer.findings, 1):
        problems = []
        bad = [s for s in f.sources if s not in calls or not calls[s].ok]
        if bad:
            problems.append(f"unknown or failed source call(s) {bad}")
        numbers = [n for s in f.sources if s in calls and calls[s].ok for n in calls[s].numbers]
        for label, v in f.values.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and not _supported(float(v), numbers):
                problems.append(f"{label}={v} does not appear in the cited tool results")
        for ev in f.evidence:
            if ev not in seen_events:
                problems.append(f"evidence id {ev} was not returned by any tool")
        findings.append(FindingOut(**f.model_dump(), verified=not problems, problems=problems))
        violations += [f"finding {i} ({f.metric}): {p}" for p in problems]
    return findings, violations


def _result_block(tool_use_id: str, payload, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": payload if isinstance(payload, str) else json.dumps(payload, default=str), "is_error": is_error}


def run_analyst(db: Session, provider: LLMProvider, question: str, match_id: int | None = None, max_steps: int | None = None) -> AnalystResult:
    max_steps = max_steps or settings.llm_max_steps
    started = time.perf_counter()
    prompt = f"[Context: the user is viewing match_id {match_id}.]\n{question}" if match_id else question
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools = tool_schemas()
    calls: dict[str, CallRecord] = {}
    trace: list[TraceStep] = []
    tokens = dict(input=0, output=0, cache_read=0, cache_write=0)
    retries = nudges = steps = 0
    final: tuple[AnswerOut, list[str]] | None = None
    status: str = "incomplete"
    message: str | None = f"No answer within {max_steps} steps."

    for step in range(1, max_steps + 1):
        steps = step
        resp = provider.chat(SYSTEM, messages, tools)
        tokens["input"] += resp.input_tokens
        tokens["output"] += resp.output_tokens
        tokens["cache_read"] += resp.cache_read_tokens
        tokens["cache_write"] += resp.cache_write_tokens
        if resp.stop_reason == "refusal":
            status, message = "refused", resp.text or "The model declined this request."
            break
        messages.append({"role": "assistant", "content": resp.content})

        if not resp.tool_calls:
            if nudges == 0:  # answered in prose instead of calling submit_answer
                nudges += 1
                messages.append({"role": "user", "content": f"Please call {SUBMIT} with your final structured answer."})
                continue
            status, message = "incomplete", "The model did not submit a structured answer."
            break

        results = []
        for tc in resp.tool_calls:
            t0 = time.perf_counter()
            if tc.name == SUBMIT:
                try:
                    answer = Answer.model_validate(tc.args)
                except ValidationError as e:
                    results.append(_result_block(tc.id, f"Invalid answer: {e.errors(include_url=False)[:3]}. Fix and call {SUBMIT} again.", True))
                    continue
                findings, violations = validate_answer(answer, calls)
                if violations and retries == 0:
                    retries += 1
                    results.append(_result_block(tc.id, "Validation failed:\n- " + "\n- ".join(violations) +
                                                 f"\nUse only numbers and event ids that appear in tool results, cite the right call_id, and call {SUBMIT} again.", True))
                    continue
                final = (AnswerOut(question=answer.question, findings=findings, interpretation=answer.interpretation,
                                   limitations=answer.limitations), violations)
                break

            call_id = f"c{len(calls) + 1}"
            ok, payload = True, None
            tool = TOOLS.get(tc.name)
            try:
                if tool is None:
                    raise ToolError(f"Unknown tool {tc.name!r}. Available: {sorted(TOOLS)} and {SUBMIT}.")
                try:
                    args = tool.args.model_validate(tc.args)
                except ValidationError as e:
                    raise ToolError(f"Invalid arguments: {e.errors(include_url=False, include_input=False)[:3]}") from e
                payload = tool.fn(db, args)
                events, numbers = collect(payload)
                text = json.dumps(payload, default=str)
                if len(text) > MAX_RESULT_CHARS:
                    raise ToolError("Result too large; narrow the request with filters or a smaller limit.")
                calls[call_id] = CallRecord(call_id, tc.name, True, events, numbers)
                body = {"call_id": call_id, **payload}
            except ToolError as e:
                ok, body = False, {"call_id": call_id, "error": str(e)}
                calls[call_id] = CallRecord(call_id, tc.name, False)
            except Exception:  # a bug in a tool must not kill the conversation
                logger.exception("tool crashed: %s", tc.name)
                ok, body = False, {"call_id": call_id, "error": "Internal error in this tool; try a different approach."}
                calls[call_id] = CallRecord(call_id, tc.name, False)
            ms = int((time.perf_counter() - t0) * 1000)
            summary = body.get("error") or f"{len(json.dumps(body, default=str))} chars, {len(calls[call_id].event_ids)} event ids"
            trace.append(TraceStep(step=step, tool=tc.name, call_id=call_id, args=tc.args, ok=ok, ms=ms, summary=summary[:300]))
            logger.info(json.dumps({"event": "tool", "step": step, "tool": tc.name, "call_id": call_id, "ok": ok, "ms": ms}))
            results.append(_result_block(tc.id, body, not ok))
        if final:
            break
        messages.append({"role": "user", "content": results})

    answer_out, violations = final if final else (None, [])
    if final:
        status, message = ("answered" if not violations else "unverified"), (None if not violations else "Some findings could not be verified against tool results.")
    usage = Usage(
        model=provider.model, steps=steps, tool_calls=len(calls), input_tokens=tokens["input"], output_tokens=tokens["output"],
        cache_read_tokens=tokens["cache_read"],
        cost_usd=cost_usd(provider.model, tokens), latency_ms=int((time.perf_counter() - started) * 1000),
    )
    logger.info(json.dumps({"event": "answer", "status": status, **usage.model_dump()}))
    return AnalystResult(status=status, answer=answer_out, message=message,
                         validation=Validation(passed=bool(final) and not violations, violations=violations), trace=trace, usage=usage)
