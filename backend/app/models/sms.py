from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SmsChallenge(Base):
    __tablename__ = 'sms_challenges'
    phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    scene: Mapped[str] = mapped_column(String(30), primary_key=True)
    out_id: Mapped[str] = mapped_column(String(64), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), default='', nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    local: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
