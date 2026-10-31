from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field


class TrainingRecordCreate(BaseModel):
    training_type: str = Field(min_length=1, max_length=80)
    task_id: Optional[str] = Field(default=None, max_length=80)
    request_key: Optional[str] = Field(default=None, min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    reps: int = Field(default=0, ge=0, le=10000)
    recording_method: Literal["manual", "pose"] = "manual"
    duration_seconds: int = Field(ge=1, le=14400)
    score: float = Field(ge=0, le=100)
    advice: str = Field(default="", max_length=5000)
    media_url: Optional[str] = Field(default=None, max_length=1000)
    media_type: Optional[Literal["image", "video"]] = None


class TrainingAdviceUpdate(BaseModel):
    advice: str = Field(min_length=1, max_length=5000)


class TrainingMediaUpdate(BaseModel):
    media_id: int = Field(gt=0)


class TrainingRecordResponse(BaseModel):
    id: int
    training_type: str
    task_id: Optional[str] = None
    reps: int = 0
    recording_method: str = "manual"
    duration_seconds: int
    score: float
    advice: str
    media_url: Optional[str]
    media_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingHistoryResponse(BaseModel):
    records: list[TrainingRecordResponse]
    has_more: bool = False
