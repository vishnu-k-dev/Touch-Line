from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SeasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class CompetitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    country: str
    seasons: list[SeasonOut]


class TeamRef(BaseModel):
    id: int
    name: str


class MatchOut(BaseModel):
    id: int
    date: date
    stage: str
    competition_id: int
    season_id: int
    home_team: TeamRef
    away_team: TeamRef
    home_score: int
    away_score: int


class MatchDetail(MatchOut):
    event_count: int
    shot_count: int


class TeamStats(BaseModel):
    team_id: int
    team: str
    goals: int
    shots: int
    shots_on_target: int
    xg: float
    np_xg: float
    xg_per_shot: float
    passes: int
    passes_completed: int
    pass_accuracy_pct: float
    pass_share_pct: float
    pressures: int
    fouls_committed: int
    corners: int
    ppda: float | None
    ppda_passes_allowed: int
    ppda_defensive_actions: int
    shootout_goals: int | None


class MatchStatsOut(BaseModel):
    match_id: int
    home: TeamStats
    away: TeamStats
    definitions: dict[str, str]


class ShotOut(BaseModel):
    event_id: str  # StatsBomb event UUID: the evidence reference
    team_id: int
    team: str
    player_id: int
    player: str
    display_name: str  # the common name (nickname) where StatsBomb has one, else the full name
    period: int
    minute: int
    second: int
    x: float | None
    y: float | None
    xg: float | None
    outcome: str
    shot_type: str | None
    body_part: str | None
    is_shootout: bool
    # 360 freeze-frame context; null if the event has no frame. defenders_in_cone counts VISIBLE defenders in the
    # shooting lane: a lower bound (reliable when positive, a zero does not prove a clear lane); use only if cone_visible.
    defenders_in_cone: int | None
    cone_visible: bool | None
    nearest_defender: float | None


class HeatmapOut(BaseModel):
    match_id: int
    team_id: int | None
    player_id: int | None
    kind: str
    cols: int
    rows: int
    cell_yards: float
    total: int
    max: int
    cells: list[list[int]]  # cells[row][col]; col runs toward the opponent's goal, row across the pitch


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    match_id: int | None = None


class HistoryTurn(BaseModel):
    id: int
    match_id: int | None
    question: str
    created_at: datetime
    result: dict  # an AnalystResult, exactly as it was returned when the question was asked


class AnalystStatus(BaseModel):
    configured: bool
    provider: str
    model: str


class SearchHit(BaseModel):
    id: int
    kind: str
    title: str
    content: str
    match_id: int | None
    score: float  # cosine similarity, higher is closer
    meta: dict  # for shot sequences: event_ids (evidence), player, team, xg, outcome, ...


class PlayerStatsOut(BaseModel):
    player_id: int
    player: str
    display_name: str
    team: str | None
    shots: int
    goals: int
    xg: float
    np_xg: float
    passes: int
    passes_completed: int
    key_passes: int
    assists: int
    pressures: int
    tackles: int
    interceptions: int
    minutes: float  # on the pitch, periods 1-4 (0 if the player did not play)
    started: bool
