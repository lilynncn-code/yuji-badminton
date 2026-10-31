from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ClinicQuestion(Base):
    __tablename__ = 'clinic_questions'
    __table_args__ = {'sqlite_autoincrement':True}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    video_url: Mapped[str] = mapped_column(String(1000), default='')
    accepted_answer_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClinicAnswer(Base):
    __tablename__ = 'clinic_answers'
    __table_args__ = {'sqlite_autoincrement':True}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('clinic_questions.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClinicSend(Base):
    __tablename__ = 'clinic_sends'
    __table_args__ = (UniqueConstraint('user_id','request_key',name='uq_clinic_user_request'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'),index=True)
    request_key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(20))
    question_id: Mapped[int] = mapped_column(Integer,index=True)
    answer_id: Mapped[int] = mapped_column(Integer,default=0)
    content_hash: Mapped[str] = mapped_column(String(64))
