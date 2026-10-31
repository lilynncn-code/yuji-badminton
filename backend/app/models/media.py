from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_name: Mapped[str] = mapped_column(String(255), default='', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")


class TrainingVideoUpload(Base):
    __tablename__ = 'training_video_uploads'
    __table_args__ = (UniqueConstraint('user_id', 'request_key'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    request_key: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64), default='')
    # Keep the original identity after media deletion, including on SQLite id reuse.
    media_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_name: Mapped[str] = mapped_column(String(255), default='')
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
