from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Game(Base):
    __tablename__ = 'games'
    __table_args__ = (UniqueConstraint('host_id','request_key',name='uq_game_host_request'),{'sqlite_autoincrement':True})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80), index=True)
    venue: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    cost_note: Mapped[str] = mapped_column(String(200), default='')
    note: Mapped[str] = mapped_column(String(1000), default='')
    status: Mapped[str] = mapped_column(String(20), default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    request_key: Mapped[Optional[str]] = mapped_column(String(64),nullable=True)


class GameMember(Base):
    __tablename__ = 'game_members'
    __table_args__ = (UniqueConstraint('game_id', 'user_id', name='uq_game_member'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey('games.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
