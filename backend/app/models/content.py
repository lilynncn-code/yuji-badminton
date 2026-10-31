from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Ranking(Base):
    __tablename__ = "rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    discipline: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    player_names: Mapped[str] = mapped_column(String(200), nullable=False)
    countries: Mapped[str] = mapped_column(String(200), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(80), nullable=False)
    prize: Mapped[str] = mapped_column(String(80), nullable=False)
    venue: Mapped[str] = mapped_column(String(160), nullable=False)
    schedule_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class News(Base):
    __tablename__ = "news"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Match(Base):
    """后台保存的比赛快照。来源失败时保留这张表里的上一次内容。"""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    event_name: Mapped[str] = mapped_column(String(160), nullable=False)
    discipline: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    round: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    court: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    player1: Mapped[str] = mapped_column(String(200), nullable=False)
    player2: Mapped[str] = mapped_column(String(200), nullable=False)
    score1: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    score2: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    score_text: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    winner: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    image_source: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    report: Mapped[str] = mapped_column(Text, nullable=False, default="")
    replay_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MatchSyncState(Base):
    __tablename__ = "match_sync_state"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default="matches")
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
