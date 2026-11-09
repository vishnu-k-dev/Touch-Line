from typing import Literal

import re

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.agents.analyst import AnalystResult, run_analyst
from app.agents.llm import DEFAULT_MODELS, AnalystUnavailable, LLMError, LLMProvider, make_provider, resolve_api_key, resolved_model
from app.core.config import settings
from app.core.db import get_db
from app.core.limits import Limiter, client_id, get_limiter
from app.models.tables import ChatTurn, Competition, Event, Match, Shot
from app.schemas.football import (
    AnalystStatus, ChatRequest, CompetitionOut, HeatmapOut, HistoryTurn, MatchDetail, MatchOut, MatchStatsOut, PlayerStatsOut,
    SearchHit, ShotOut, TeamRef,
)
from app.services import analytics, rag

router = APIRouter(prefix="/api/v1")

MAX_TURNS_PER_VISITOR = 100
_VISITOR = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def visitor_id(x_visitor_id: str | None = Header(default=None)) -> str | None:
    """The browser's anonymous id (header X-Visitor-Id). Without it nothing is stored."""
    if x_visitor_id is not None and not _VISITOR.match(x_visitor_id):
        raise HTTPException(422, "X-Visitor-Id must be 8-64 letters, digits, '-' or '_'")
    return x_visitor_id


def _save_turn(db: Session, visitor: str, match_id: int | None, question: str, result: AnalystResult) -> None:
    db.add(ChatTurn(visitor_id=visitor, match_id=match_id, question=question, result=result.model_dump(mode="json")))
    db.flush()
    keep = select(ChatTurn.id).where(ChatTurn.visitor_id == visitor).order_by(ChatTurn.id.desc()).limit(MAX_TURNS_PER_VISITOR)
    db.execute(delete(ChatTurn).where(ChatTurn.visitor_id == visitor, ChatTurn.id.not_in(keep)))
    db.commit()


def get_provider() -> LLMProvider:
    """Dependency: the configured LLM, or a clear 503 when the analyst is not set up."""
    try:
        return make_provider()
    except AnalystUnavailable as e:
        raise HTTPException(503, str(e)) from e


def _match_out(m: Match) -> dict:
    return {
        "id": m.id, "date": m.match_date, "stage": m.stage, "competition_id": m.competition_id,
        "season_id": m.season_id, "home_team": TeamRef(id=m.home_team.id, name=m.home_team.name),
        "away_team": TeamRef(id=m.away_team.id, name=m.away_team.name),
        "home_score": m.home_score, "away_score": m.away_score,
    }


def _found(result):
    if result is None:
        raise HTTPException(404, "Match not found")
    return result


@router.get("/competitions", response_model=list[CompetitionOut])
def competitions(db: Session = Depends(get_db)):
    # validate inside the handler: the session is closed before FastAPI serialises the return value
    return [CompetitionOut.model_validate(c) for c in db.scalars(select(Competition).order_by(Competition.name))]


@router.get("/matches", response_model=list[MatchOut])
def matches(competition_id: int | None = None, season_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Match).order_by(Match.match_date, Match.id)
    if competition_id is not None:
        q = q.where(Match.competition_id == competition_id)
    if season_id is not None:
        q = q.where(Match.season_id == season_id)
    return [_match_out(m) for m in db.scalars(q)]


@router.get("/matches/{match_id}", response_model=MatchDetail)
def match(match_id: int, db: Session = Depends(get_db)):
    m = _found(db.get(Match, match_id))
    return {
        **_match_out(m),
        "event_count": db.scalar(select(func.count()).select_from(Event).where(Event.match_id == match_id)),
        "shot_count": db.scalar(select(func.count()).select_from(Shot).where(Shot.match_id == match_id)),
    }


@router.get("/matches/{match_id}/stats", response_model=MatchStatsOut)
def match_stats(match_id: int, db: Session = Depends(get_db)):
    return _found(analytics.match_stats(db, match_id))


@router.get("/matches/{match_id}/shots", response_model=list[ShotOut])
def match_shots(match_id: int, include_shootout: bool = Query(False), db: Session = Depends(get_db)):
    return _found(analytics.shot_map(db, match_id, include_shootout))


@router.get("/matches/{match_id}/players", response_model=list[PlayerStatsOut])
def match_players(match_id: int, db: Session = Depends(get_db)):
    return _found(analytics.player_stats(db, match_id))


@router.get("/matches/{match_id}/heatmap", response_model=HeatmapOut)
def match_heatmap(
    match_id: int,
    player_id: int | None = None,
    team_id: int | None = None,
    kind: Literal["actions", "passes", "pressures", "shots"] = "actions",
    db: Session = Depends(get_db),
):
    """Action counts per 10-yard pitch cell for one player or one team (give player_id or team_id)."""
    if player_id is None and team_id is None:
        raise HTTPException(422, "Provide player_id or team_id")
    return _found(analytics.heatmap(db, match_id, team_id, player_id, kind))


@router.get("/analyst/status", response_model=AnalystStatus)
def analyst_status():
    provider = settings.llm_provider.lower()
    return {"configured": provider in DEFAULT_MODELS and bool(resolve_api_key()), "provider": provider, "model": resolved_model()}


@router.post("/analyst/chat", response_model=AnalystResult)
def analyst_chat(
    req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_provider),
    limits: Limiter = Depends(get_limiter),
    visitor: str | None = Depends(visitor_id),
):
    """Ask the AI analyst. The agent picks analytical tools, and every finding in the answer cites the tool results and
    event ids behind it; `validation` reports whether those citations check out. Rate-limited and spend-capped."""
    if req.match_id is not None and db.get(Match, req.match_id) is None:
        raise HTTPException(404, "Match not found")
    limits.acquire(client_id(request))
    cost = None
    charged = False
    try:
        result = run_analyst(db, provider, req.question, req.match_id)
        cost, charged = result.usage.cost_usd, True
        if visitor:
            _save_turn(db, visitor, req.match_id, req.question, result)
        return result
    except AnalystUnavailable as e:
        raise HTTPException(503, str(e)) from e
    except LLMError as e:
        raise HTTPException(502, f"The language model call failed: {e}") from e
    finally:
        limits.release(cost, charged)


@router.get("/analyst/history", response_model=list[HistoryTurn])
def analyst_history(match_id: int | None = None, db: Session = Depends(get_db), visitor: str | None = Depends(visitor_id)):
    """This visitor's earlier questions and answers, oldest first. Empty without an X-Visitor-Id."""
    if not visitor:
        return []
    q = select(ChatTurn).where(ChatTurn.visitor_id == visitor).order_by(ChatTurn.id)
    if match_id is not None:
        q = q.where(ChatTurn.match_id == match_id)
    return [
        {"id": t.id, "match_id": t.match_id, "question": t.question, "created_at": t.created_at, "result": t.result}
        for t in db.scalars(q)
    ]


@router.delete("/analyst/history")
def clear_analyst_history(match_id: int | None = None, db: Session = Depends(get_db), visitor: str | None = Depends(visitor_id)):
    """Delete this visitor's saved questions (all, or just one match's)."""
    if not visitor:
        return {"deleted": 0}
    q = delete(ChatTurn).where(ChatTurn.visitor_id == visitor)
    if match_id is not None:
        q = q.where(ChatTurn.match_id == match_id)
    deleted = db.execute(q).rowcount
    db.commit()
    return {"deleted": deleted}


@router.get("/search", response_model=list[SearchHit])
def search(
    q: str = Query(min_length=2, max_length=300),
    k: int = Query(5, ge=1, le=20),
    kind: Literal["knowledge", "match", "sequence"] | None = None,
    match_id: int | None = None,
    team: str | None = None,
    player: str | None = None,
    outcome: str | None = None,
    shot_type: str | None = None,
    body_part: str | None = None,
    play_pattern: str | None = None,
    db: Session = Depends(get_db),
):
    """Semantic search over tactical knowledge, match summaries and shot sequences. Filters match shot-sequence metadata exactly."""
    filters = {k_: v for k_, v in dict(
        team=team, player=player, outcome=outcome, shot_type=shot_type, body_part=body_part, play_pattern=play_pattern
    ).items() if v}
    return rag.search(db, q, k, kind, match_id, filters)
