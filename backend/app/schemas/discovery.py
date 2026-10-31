from typing import List, Optional

from pydantic import BaseModel, Field


class PlayerCard(BaseModel):
    id: int
    name: str
    avatar: str
    city: str
    level: str
    distance: str
    distance_text: str
    bio: str
    favorite_area: str
    play_time: str
    tags: List[str]


class PlayerDetail(PlayerCard):
    age: Optional[int] = None
    gender: str = ""
    years_playing: str
    grip: str
    recent_activity: str
    preferred_venues: List[str]
    match_note: str


class VenueCard(BaseModel):
    id: int
    name: str
    avatar: str
    city: str
    level: str
    distance: str
    distance_text: str
    bio: str
    address: str
    open_time: str
    price_text: str
    tags: List[str]


class DiscoveryListResponse(BaseModel):
    total: int
    items: List[PlayerCard]


class VenueListResponse(BaseModel):
    total: int
    items: List[VenueCard]


class DiscoverySearchResponse(BaseModel):
    players: List[PlayerCard]
    venues: List[VenueCard]


class DiscoveryQuery(BaseModel):
    city: Optional[str] = Field(default=None, max_length=80)
    level: Optional[str] = Field(default=None, max_length=80)
    keyword: Optional[str] = Field(default=None, max_length=80)
