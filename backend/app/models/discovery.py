from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiscoveryPlayer(Base):
    __tablename__ = "discovery_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    distance: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    distance_text: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    favorite_area: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    play_time: Mapped[str] = mapped_column(String(120), default="", nullable=False)


class DiscoveryVenue(Base):
    __tablename__ = "discovery_venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    distance: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    distance_text: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    address: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    open_time: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    price_text: Mapped[str] = mapped_column(String(80), default="", nullable=False)
