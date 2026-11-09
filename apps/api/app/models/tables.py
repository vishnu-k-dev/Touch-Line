from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str]
    country: Mapped[str]
    seasons: Mapped[list["Season"]] = relationship(back_populates="competition")


class Season(Base):
    # StatsBomb season ids repeat across competitions, so the key is (competition_id, id)
    __tablename__ = "seasons"
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), primary_key=True, autoincrement=False)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str]
    competition: Mapped[Competition] = relationship(back_populates="seasons")


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str]


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str]
    nickname: Mapped[str | None]
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        ForeignKeyConstraint(["competition_id", "season_id"], ["seasons.competition_id", "seasons.id"]),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    competition_id: Mapped[int]
    season_id: Mapped[int]
    match_date: Mapped[date]
    stage: Mapped[str]
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_score: Mapped[int]
    away_score: Mapped[int]
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])


class PlayerMinutes(Base):
    """Minutes on the pitch per player per match, from lineup position spells (periods 1-4; shootout excluded)."""

    __tablename__ = "player_minutes"
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    jersey_number: Mapped[int | None]
    minutes: Mapped[float]  # 0 for unused substitutes
    started: Mapped[bool]


class Event(Base):
    """One StatsBomb event. `id` is the UUID the agent cites as evidence; `raw_data` keeps the full original JSON."""

    __tablename__ = "events"
    __table_args__ = (Index("ix_events_match_type", "match_id", "type"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    idx: Mapped[int]
    period: Mapped[int]  # 1-2 normal time, 3-4 extra time, 5 = penalty shootout
    minute: Mapped[int]
    second: Mapped[int]
    type: Mapped[str]
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    x: Mapped[float | None]  # 120 x 80 pitch, every team attacks toward x=120
    y: Mapped[float | None]
    possession: Mapped[int]
    raw_data: Mapped[dict] = mapped_column(JSONB)


class Shot(Base):
    __tablename__ = "shots"
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    period: Mapped[int]
    minute: Mapped[int]
    second: Mapped[int]
    x: Mapped[float | None]
    y: Mapped[float | None]
    xg: Mapped[float | None]
    outcome: Mapped[str]
    shot_type: Mapped[str | None]  # Open Play, Penalty, Free Kick
    body_part: Mapped[str | None]
    technique: Mapped[str | None]
    is_shootout: Mapped[bool]
    # From the 360 freeze-frame (null when the event has no frame). A LOWER BOUND, see services/geometry.py.
    defenders_in_cone: Mapped[int | None]  # visible opponents (not the keeper) inside the triangle ball-post-post
    cone_visible: Mapped[bool | None]  # was the whole shooting lane inside the camera's visible area
    nearest_defender: Mapped[float | None]  # yards to the nearest visible opponent outfield player


EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5


class Document(Base):
    """A retrievable text chunk. kind: 'knowledge' (tactical concepts), 'match' (match summary) or 'sequence' (a shot and how it was created)."""

    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(index=True)
    title: Mapped[str]
    content: Mapped[str]
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), index=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)  # evidence: event_ids, team, minute, xg, play_pattern, ...
    embedding = mapped_column(Vector(EMBEDDING_DIM))


class ChatTurn(Base):
    """One question to the analyst and its full result, kept per anonymous visitor so a conversation survives reloads,
    match switches and restarts. `visitor_id` is a random id the browser generates; it is not an account."""

    __tablename__ = "chat_turns"
    __table_args__ = (Index("ix_chat_turns_visitor_match", "visitor_id", "match_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    visitor_id: Mapped[str]
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"))
    question: Mapped[str]
    result: Mapped[dict] = mapped_column(JSONB)  # the AnalystResult as returned to the browser
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
