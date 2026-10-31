from typing import Optional

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: int
    can_review_reports: bool = False
    following: int = 0
    followers: int = 0
    username: str
    phone: str
    name: str
    nickname: str
    avatar: str
    city: str
    level_tag: str
    levelTag: str
    level: str
    cover: str = ""
    club: str = ""
    hand: str = "右手持拍"
    bio: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)
    nickname: Optional[str] = Field(default=None, max_length=50)
    cover: Optional[str] = Field(default=None, max_length=500)
    club: Optional[str] = Field(default=None, max_length=80)
    hand: Optional[str] = Field(default=None, max_length=20)
    avatar: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=80)
    level_tag: Optional[str] = Field(default=None, max_length=80)
    levelTag: Optional[str] = Field(default=None, max_length=80)
    level: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=500)
