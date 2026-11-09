"""Evaluate the analyst on golden questions. Ground truth is computed from the database (whose metrics are themselves
tested against the raw StatsBomb files), so the expected numbers cannot drift from the data.

    cd apps/api && python -m app.evals.agent_eval                       # the configured model
    cd apps/api && python -m app.evals.agent_eval --model gpt-5.6-terra --out terra.json   # compare models

Needs LLM_API_KEY (or OPENAI_API_KEY / ANTHROPIC_API_KEY) and spends real money: roughly 9 questions x 5-8 model turns.
Reported per run: pass rate, groundedness, tool use, latency and cost, so models and prompts can be compared."""

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agents.analyst import AnalystResult, run_analyst
from app.agents.llm import AnalystUnavailable, LLMError, make_provider
from app.core.config import settings
from app.core.db import SessionLocal
from app.services import analytics

DECLINE_WORDS = ("formation", "tracking", "speed", "predict", "future", "not available", "cannot", "can't", "no data", "unable")


@dataclass
class Case:
    id: str
    question: str
    match_id: int | None = None
    expect_tools: list[str] = field(default_factory=list)  # at least one of these must be called
    expect_numbers: list[float] = field(default_factory=list)  # each must appear in some finding's values
    must_decline: bool = False  # the data cannot answer: expect no findings and an explanation in limitations


def build_cases(db: Session) -> list[Case]:
    saudi, final, moro = (analytics.match_stats(db, m) for m in (3857300, 3869685, 3869220))
    germany = analytics.match_stats(db, 3857284)["home"]["team_id"]
    clear_lane = sum(1 for s in analytics.shot_map(db, 3857284) if s["team_id"] == germany and s["cone_visible"] and s["defenders_in_cone"] == 0)
    players = analytics.player_stats(db, 3869685)
    messi = next(p for p in players if "Messi" in p["player"])
    mbappe = next(p for p in players if "Mbapp" in p["player"])
    return [
        Case("upset_xg", "Argentina had far more shots than Saudi Arabia but lost. Why?", 3857300,
             ["get_match_summary", "get_shot_map"], [saudi["home"]["xg"], saudi["away"]["xg"]]),
        Case("player_compare", "Compare Messi and MbappÃ© in the final.", 3869685,
             ["compare_players", "get_player_stats"], [messi["goals"], mbappe["goals"]]),
        Case("pressing_ppda", "Which team pressed more intensely in Morocco vs Spain, and by how much?", 3869220,
             ["calculate_ppda", "get_match_summary"], [moro["home"]["ppda"], moro["away"]["ppda"]]),
        Case("shootout", "Who won the penalty shootout in the final and how many penalties did each side score?", 3869685,
             ["get_match_summary", "get_shot_map"], [final["home"]["shootout_goals"], final["away"]["shootout_goals"]]),
        Case("knowledge_ppda", "What does PPDA measure and what are its limits?", None, ["search_tactical_knowledge"], []),
        Case("lane_360", "How many of Germany's shots against Japan had no visible defender in the shooting lane?", 3857284,
             ["get_shot_map"], [clear_lane]),
        Case("find_match", "Which World Cup match here ended 1-2 with the losing side having much more xG, and what were the scorelines?", None,
             ["list_matches", "search_tactical_knowledge"], []),
        Case("decline_formation", "What formation did France use in the final and how fast did MbappÃ© sprint?", 3869685, [], [], True),
        Case("decline_future", "Who will win the next World Cup?", None, [], [], True),
    ]


def score_case(case: Case, r: AnalystResult) -> dict:
    called = {t.tool for t in r.trace}
    values = [v for f in (r.answer.findings if r.answer else []) for v in f.values.values() if isinstance(v, (int, float))]
    limitations = " ".join(r.answer.limitations).lower() if r.answer else ""
    out = {
        "answered": r.status in ("answered", "unverified"),
        "grounded": r.status == "answered" and r.validation.passed,
        "tools_ok": not case.expect_tools or any(t in called for t in case.expect_tools),
        "numbers_ok": all(any(abs(v - n) <= 0.0051 for v in values) for n in case.expect_numbers),
    }
    if case.must_decline:
        out["declined_ok"] = bool(r.answer) and not r.answer.findings and any(w in limitations for w in DECLINE_WORDS)
    checks = [out["answered"], out["grounded"], out["tools_ok"], out["numbers_ok"]] + ([out["declined_ok"]] if case.must_decline else [])
    out["passed"] = all(checks)
    return out


def run_eval(db: Session, provider, cases: list[Case]) -> dict:
    rows = []
    for c in cases:
        try:
            r = run_analyst(db, provider, c.question, c.match_id)
            row = {"id": c.id, **score_case(c, r), "status": r.status, "steps": r.usage.steps, "tool_calls": r.usage.tool_calls,
                   "latency_ms": r.usage.latency_ms, "tokens": r.usage.input_tokens + r.usage.output_tokens, "cost_usd": r.usage.cost_usd,
                   "violations": r.validation.violations}
        except LLMError as e:
            row = {"id": c.id, "passed": False, "error": str(e)}
        rows.append(row)
        print(f"{'PASS' if row['passed'] else 'FAIL'}  {c.id:<18} {row.get('latency_ms', '-'):>6} ms  ${row.get('cost_usd') or 0:.3f}  {row.get('error', '')}", flush=True)
    done = [r for r in rows if "latency_ms" in r]
    cost = [r["cost_usd"] for r in done if r["cost_usd"] is not None]
    return {
        "model": provider.model,
        "cases": len(rows),
        "pass_rate": round(sum(r["passed"] for r in rows) / len(rows), 2),
        "grounded_rate": round(sum(r.get("grounded", False) for r in rows) / len(rows), 2),
        "numbers_correct_rate": round(sum(r.get("numbers_ok", False) for r in rows) / len(rows), 2),
        "median_latency_s": round(statistics.median(r["latency_ms"] for r in done) / 1000, 1) if done else None,
        "mean_tool_calls": round(statistics.mean(r["tool_calls"] for r in done), 1) if done else None,
        "total_cost_usd": round(sum(cost), 3) if cost else None,
        "cost_per_question_usd": round(sum(cost) / len(cost), 3) if cost else None,
        "results": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["openai", "anthropic"], help="default: LLM_PROVIDER")
    ap.add_argument("--model", help="default: the provider's default model")
    ap.add_argument("--effort", help="reasoning effort, default: LLM_EFFORT")
    ap.add_argument("--out", help="write the full report as JSON")
    args = ap.parse_args(argv)
    if args.provider:
        settings.llm_provider = args.provider
    if args.model:
        settings.llm_model = args.model
    elif args.provider:
        settings.llm_model = ""  # the other provider's model name would not make sense
    if args.effort is not None:
        settings.llm_effort = args.effort
    try:
        provider = make_provider()
    except AnalystUnavailable as e:
        print(f"{e} The eval calls the live model.", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        report = run_eval(db, provider, build_cases(db))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
