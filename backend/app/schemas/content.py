from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


RankingDiscipline = Literal["men_single", "women_single", "men_double", "women_double", "mixed_double"]
EventStatus = Literal["upcoming", "ongoing", "finished"]


class RankingPlayer(BaseModel):
    name: str
    country: str


class RankingItem(BaseModel):
    rank: int
    previous_rank: Optional[int] = None
    points: int
    updated_at: datetime
    source_url: HttpUrl
    players: list[RankingPlayer]


class RankingListResponse(BaseModel):
    discipline: RankingDiscipline
    title: str
    updated_at: datetime
    source_url: HttpUrl
    items: list[RankingItem]


class EventListItem(BaseModel):
    id: str
    title: str
    start_date: date
    end_date: date
    location: str
    status: EventStatus
    image_url: HttpUrl
    updated_at: datetime
    source_url: HttpUrl


class EventDetailResponse(EventListItem):
    summary: str
    level: str
    prize: str
    venue: str
    schedule: list[str] = Field(default_factory=list)


class EventListResponse(BaseModel):
    updated_at: datetime
    items: list[EventListItem]


class NewsListItem(BaseModel):
    id: str
    title: str
    summary: str
    image_url: HttpUrl
    body: str
    source: str
    source_url: HttpUrl
    published_at: datetime
    updated_at: datetime


class NewsListResponse(BaseModel):
    updated_at: datetime
    items: list[NewsListItem]


class MatchItem(BaseModel):
    id: str
    event_id: str
    event_name: str
    discipline: str
    round: str
    court: str
    scheduled_at: Optional[datetime] = None
    player1: str
    player2: str
    score1: str = ""
    score2: str = ""
    score_text: str = ""
    winner: str = ""
    status: str = "scheduled"
    image_url: str = ""
    image_source: str = ""
    report: str = ""
    replay_url: str = ""
    source_url: str = ""
    source_updated_at: Optional[datetime] = None
    saved_at: datetime


class MatchSyncInfo(BaseModel):
    latest_updated_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None
    using_old_data: bool = False
    last_error: str = ""
    source_url: str = ""
    last_attempt_at: Optional[datetime] = None


class MatchEventItem(BaseModel):
    id: str
    name: str
    start_date: date
    end_date: date
    location: str = ""
    image_url: str = ""
    source_url: str = ""
    summary: str = ""
    status: str = ""


class MatchListResponse(BaseModel):
    updated_at: Optional[datetime] = None
    events: list[MatchEventItem] = Field(default_factory=list)
    items: list[MatchItem] = Field(default_factory=list)
    sync: MatchSyncInfo


class MatchDetailResponse(BaseModel):
    item: MatchItem
    sync: MatchSyncInfo
