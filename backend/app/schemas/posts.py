from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    image_urls: list[str] = Field(default_factory=list, max_length=9)
    video_url: str = Field('', max_length=1000)
    request_key: Optional[str] = Field(None, min_length=12, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')


class PostUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    image_urls: list[str] = Field(default_factory=list, max_length=9)
    video_url: str = Field('', max_length=1000)


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    reply_to_id: Optional[int] = Field(default=None,gt=0)
    request_key: Optional[str] = Field(default=None,min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')


class PostAuthorResponse(BaseModel):
    id: int
    name: str
    avatar: str
    level_tag: str

    class Config:
        from_attributes = True


class ReplyTargetResponse(BaseModel):
    id: int
    user_id: int
    author_name: str
    content: str


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    author: PostAuthorResponse
    content: str
    reply_to_id: Optional[int] = None
    reply_to: Optional[ReplyTargetResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: int
    user_id: int
    author: PostAuthorResponse
    content: str
    image_urls: list[str]
    video_url: str = ''
    likes_count: int
    comments_count: int
    comments: list[CommentResponse] = Field(default_factory=list)
    comments_has_more: bool = False
    liked_by_me: bool
    can_edit: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    has_more: bool = False
    next_cursor: Optional[str] = None


class LikeResponse(BaseModel):
    post_id: int
    liked: bool
    likes_count: int


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    has_more: bool
