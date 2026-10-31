from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


ALLOWED_PURPOSES = {"avatar", "post", "training", "chat"}
ALLOWED_MEDIA_TYPES = {"image", "video"}


def clean_required(value: str, message: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(message)
    return cleaned


class MediaCreateRequest(BaseModel):
    purpose: str = Field(max_length=20)
    media_type: str = Field(max_length=20)
    url: str = Field(max_length=1000)

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, value: str) -> str:
        cleaned = clean_required(value, "用途不能为空")
        if cleaned not in ALLOWED_PURPOSES:
            raise ValueError("用途只能是 avatar、post、training")
        return cleaned

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        cleaned = clean_required(value, "类型不能为空")
        if cleaned not in ALLOWED_MEDIA_TYPES:
            raise ValueError("类型只能是 image、video")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return clean_required(value, "地址不能为空")


class MediaUpdateRequest(BaseModel):
    purpose: Optional[str] = Field(default=None, max_length=20)
    media_type: Optional[str] = Field(default=None, max_length=20)
    url: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("purpose")
    @classmethod
    def validate_optional_purpose(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = clean_required(value, "用途不能为空")
        if cleaned not in ALLOWED_PURPOSES:
            raise ValueError("用途只能是 avatar、post、training")
        return cleaned

    @field_validator("media_type")
    @classmethod
    def validate_optional_media_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = clean_required(value, "类型不能为空")
        if cleaned not in ALLOWED_MEDIA_TYPES:
            raise ValueError("类型只能是 image、video")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_optional_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return clean_required(value, "地址不能为空")


class MediaResponse(BaseModel):
    id: int
    purpose: str
    media_type: str
    url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int
