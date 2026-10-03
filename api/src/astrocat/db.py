"""Database models and session handling (concept §11)."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from functools import cache
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from astrocat.settings import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)  # stored lowercase
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(2), default="en")
    grammatical_gender: Mapped[str] = mapped_column(String(10), default="neutral")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    birth: Mapped["BirthProfile | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class BirthProfile(Base):
    __tablename__ = "birth_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    birth_date: Mapped[date] = mapped_column(Date)
    birth_time: Mapped[time | None] = mapped_column(Time)  # None = unknown, noon fallback
    place_name: Mapped[str] = mapped_column(String(200))
    place_id: Mapped[int | None] = mapped_column(BigInteger)  # GeoNames id, if chosen from the search
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    birth_timezone: Mapped[str] = mapped_column(String(64))
    utc_offset_override: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="birth")


class UserSession(Base):
    __tablename__ = "sessions"

    # SHA-256 of the cookie token; the token itself is never stored.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DailyReading(Base):
    __tablename__ = "daily_readings"
    __table_args__ = (UniqueConstraint("user_id", "local_date", "language", "input_hash", name="uq_reading_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(Date)
    language: Mapped[str] = mapped_column(String(2))
    input_hash: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(12))  # generating / ok / fallback / failed
    engine_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reading_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[Any] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    engine_version: Mapped[str | None] = mapped_column(String(32))
    duration_s: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Place(Base):
    """A city from GeoNames cities1000 (CC BY 4.0)."""

    __tablename__ = "places"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # GeoNames id
    name: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(64))
    population: Mapped[int] = mapped_column(BigInteger, default=0)


class PlaceName(Base):
    """Searchable names of a place: lowercase, without accents (Munich, muenchen, munchen …)."""

    __tablename__ = "place_names"
    __table_args__ = (Index("ix_place_names_prefix", "name_norm", postgresql_ops={"name_norm": "text_pattern_ops"}),)

    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), primary_key=True)
    name_norm: Mapped[str] = mapped_column(Text, primary_key=True)


@cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@cache
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with session_factory()() as db:
        yield db
