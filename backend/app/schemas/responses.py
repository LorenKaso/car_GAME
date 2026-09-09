from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProfileOutput(Output):
    id: UUID
    username: str
    display_name: str
    avatar_reference: str | None
    country: str | None
    coins: int
    xp: int
    level: int
    created_at: datetime
    updated_at: datetime


class CurrentUserOutput(Output):
    id: UUID
    email: str
    email_verified: bool
    profile: ProfileOutput


class TokenOutput(Output):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class MessageOutput(Output):
    message: str


class CarOutput(Output):
    id: UUID
    name: str
    manufacturer: str
    model: str
    base_top_speed_kph: int
    acceleration: int
    handling: int
    braking: int
    boost: int
    asset_identifier: str


class OwnedCarOutput(Output):
    id: UUID
    is_selected: bool
    created_at: datetime
    car: CarOutput


class LocationOutput(Output):
    id: UUID
    slug: str
    name: str
    country: str
    status: str
