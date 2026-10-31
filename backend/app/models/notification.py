from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Notification(Base):
    __tablename__ = 'notifications'
    __table_args__ = (UniqueConstraint('user_id','event_key',name='uq_notification_event'),)
    id: Mapped[int] = mapped_column(Integer,primary_key=True,index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'),index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'),index=True)
    kind: Mapped[str] = mapped_column(String(30))
    target_type: Mapped[str] = mapped_column(String(20),index=True)
    target_id: Mapped[int] = mapped_column(Integer,index=True)
    context_id: Mapped[int] = mapped_column(Integer,default=0)
    event_key: Mapped[Optional[str]] = mapped_column(String(100),nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow,nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime,nullable=True)
