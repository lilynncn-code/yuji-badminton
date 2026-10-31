from typing import List, Optional

from pydantic import BaseModel, Field


class TrainingAdviceRequest(BaseModel):
    lesson_name: str = Field(default="羽毛球训练", max_length=80)
    reps: int = Field(default=0, ge=0)
    score: float = Field(default=0, ge=0)
    confidence: float = Field(default=0, ge=0)
    duration_seconds: int = Field(default=30, ge=0)
    feedback: str = Field(default="", max_length=500)


class TrainingAdviceResponse(BaseModel):
    advice: str
    improvement: str
    source: str


class AmapCourtQuery(BaseModel):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    radius: int = Field(default=5000, ge=100, le=50000)
    keyword: str = Field(default="羽毛球馆", max_length=80)
    page: int = Field(default=1, ge=1, le=100)


class AmapCityCourtQuery(BaseModel):
    city: str = Field(min_length=1, max_length=80)
    keyword: str = Field(default='羽毛球馆', max_length=80)
    page: int = Field(default=1, ge=1, le=100)


class AmapCourtItem(BaseModel):
    id: str
    name: str
    address: str
    distance: str
    hours: str
    location: Optional[str] = ""
    tel: Optional[str] = ""
    features: List[str] = Field(default_factory=list)


class AmapCourtResponse(BaseModel):
    source: str
    message: str = ""
    items: List[AmapCourtItem]
    has_more: bool = False


class AmapStatusResponse(BaseModel):
    ready: bool
    message: str
