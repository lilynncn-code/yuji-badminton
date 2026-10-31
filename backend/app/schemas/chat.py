from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatApplyRequest(BaseModel):
    receiver_id: int = Field(gt=0)
    note: str = Field(default="", max_length=300)


class ChatReadRequest(BaseModel):
    last_message_id: int = Field(ge=0)


class ChatTextMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatImageMessageRequest(BaseModel):
    image_url: str = Field(min_length=1, max_length=1000)


class ChatVoiceReplyResponse(BaseModel):
    text: str
    audio_base64: str = ""
    audio_format: str = "pcm"
    sample_rate: int = 24000
    source: str


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    message_type: Literal["text", "image", "voice"]
    content: str
    created_at: datetime
    recalled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatCombinedRequest(BaseModel):
    content: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=1000)
    request_key: Optional[str] = Field(default=None, min_length=8, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')


class ChatResponse(BaseModel):
    id: int
    requester_id: int
    receiver_id: int
    other_user_id: Optional[int] = None
    other_name: str = ""
    other_avatar: str = ""
    note: str = ""
    unread_count: int = 0
    other_read_id: int = 0
    status: Literal["pending", "accepted", "rejected"]
    created_at: datetime
    updated_at: datetime
    last_message: Optional[ChatMessageResponse] = None

    class Config:
        from_attributes = True


class ChatInboxSummary(BaseModel):
    total_threads:int=0
    total_requests:int=0
    pending_incoming:int=0
    unread_count:int=0


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]
    has_more:bool=False
    next_cursor:Optional[str]=None
    revision:int=0
    summary:ChatInboxSummary=Field(default_factory=ChatInboxSummary)


class ChatMessagesResponse(BaseModel):
    chat: ChatResponse
    messages: list[ChatMessageResponse]
    has_more: bool = False
    message_updates: list[ChatMessageResponse] = Field(default_factory=list)
    change_cursor: int = 0


class ChatActionResponse(BaseModel):
    message: str
    chat: ChatResponse
