"""Persistence models. API output uses separate, allowlisted schemas."""

from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("game.users.id"), unique=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    display_name: Mapped[str] = mapped_column(String(60))
    avatar_reference: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("game.users.id"))
    access_hash: Mapped[str] = mapped_column(String(64), unique=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UsedRefreshToken(Base):
    __tablename__ = "used_refresh_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("game.sessions.id"))
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AccountToken(Base):
    __tablename__ = "account_tokens"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("game.users.id"))
    purpose: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Car(Base):
    __tablename__ = "cars"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    manufacturer: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    base_top_speed_kph: Mapped[int] = mapped_column(Integer)
    acceleration: Mapped[int] = mapped_column(Integer)
    handling: Mapped[int] = mapped_column(Integer)
    braking: Mapped[int] = mapped_column(Integer)
    boost: Mapped[int] = mapped_column(Integer)
    asset_identifier: Mapped[str] = mapped_column(String(120))
    is_starter: Mapped[bool] = mapped_column(Boolean)
    enabled: Mapped[bool] = mapped_column(Boolean)


class UserCar(Base):
    __tablename__ = "user_cars"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("game.users.id"))
    car_id: Mapped[UUID] = mapped_column(ForeignKey("game.cars.id"))
    grant_type: Mapped[str] = mapped_column(String(30))
    is_selected: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PlayerState(Base):
    __tablename__ = "player_state"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("game.users.id"), primary_key=True)
    coins: Mapped[int] = mapped_column(BigInteger)
    xp: Mapped[int] = mapped_column(BigInteger)
    curve_version: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LevelThreshold(Base):
    __tablename__ = "level_thresholds"
    curve_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    minimum_xp: Mapped[int] = mapped_column(BigInteger)


class EconomyTransaction(Base):
    __tablename__ = "economy_transactions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("game.users.id"))
    kind: Mapped[str] = mapped_column(String(40))
    coins_delta: Mapped[int] = mapped_column(BigInteger)
    xp_delta: Mapped[int] = mapped_column(BigInteger)
    reference_type: Mapped[str] = mapped_column(String(40))
    reference_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    payload_encrypted: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(20))
    center: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326))


class RaceZone(Base):
    __tablename__ = "race_zones"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("game.locations.id"))
    name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))
    boundary: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))


class TrackVersion(Base):
    __tablename__ = "track_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    race_zone_id: Mapped[UUID] = mapped_column(ForeignKey("game.race_zones.id"))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    manifest_key: Mapped[str | None] = mapped_column(String(240))
    gameplay_hash: Mapped[str | None] = mapped_column(String(64))
