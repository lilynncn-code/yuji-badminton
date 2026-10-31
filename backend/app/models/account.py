from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PhoneChange(Base):
    __tablename__='phone_changes'
    key_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    old_phone: Mapped[str]=mapped_column(String(20))
    new_phone: Mapped[str]=mapped_column(String(20))
    session_version: Mapped[int]=mapped_column(Integer)
    expires_at: Mapped[datetime]=mapped_column(DateTime)
    used: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)


class AccountFileDeletion(Base):
    __tablename__ = 'account_file_deletions'
    path: Mapped[str] = mapped_column(String(300), primary_key=True)
