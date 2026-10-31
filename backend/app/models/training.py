from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrainingRecord(Base):
    __tablename__ = "training_records"
    __table_args__ = (UniqueConstraint("user_id", "request_key", name="uq_training_user_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    training_type: Mapped[str] = mapped_column(String(80), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    request_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recording_method: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    advice: Mapped[str] = mapped_column(Text, default="", nullable=False)
    media_url: Mapped[Optional[str]] = mapped_column(String(1000), default=None, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(20), default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TrainingProgress(Base):
    __tablename__ = "training_progress"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    completed: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
