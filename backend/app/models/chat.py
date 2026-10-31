from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (
        UniqueConstraint("requester_id", "receiver_id", name="uq_chat_requester_receiver"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    note: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    requester_read_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    receiver_read_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    recalled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    chat: Mapped[Chat] = relationship("Chat", back_populates="messages")


class ChatState(Base):
    __tablename__ = 'chat_states'
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    cleared_through_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ChatChange(Base):
    __tablename__ = 'chat_changes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey('chat_messages.id'), nullable=False)


class ChatSend(Base):
    __tablename__ = 'chat_sends'
    __table_args__ = (UniqueConstraint('chat_id', 'user_id', 'request_key', name='uq_chat_send_request'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    request_key: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    message_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class ChatInboxRevision(Base):
    __tablename__ = 'chat_inbox_revisions'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'),primary_key=True)
    revision: Mapped[int] = mapped_column(Integer,default=0,nullable=False)
