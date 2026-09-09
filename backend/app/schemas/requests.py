import re
import unicodedata
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Password = Annotated[str, Field(min_length=15, max_length=128)]
Token = Annotated[str, Field(min_length=40, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmailRequest(StrictRequest):
    email: EmailStr = Field(max_length=254)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class RegisterRequest(EmailRequest):
    username: str = Field(min_length=3, max_length=30)
    display_name: str = Field(min_length=1, max_length=60)
    password: Password
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value):
        value = value.lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", value):
            raise ValueError(
                "Use 3-30 ASCII letters, digits or underscores, starting with a letter"
            )
        return value

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value or any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("Display name cannot be blank or contain control characters")
        return value


class LoginRequest(EmailRequest):
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(StrictRequest):
    refresh_token: Token


class TokenRequest(StrictRequest):
    token: Token


class ResetPasswordRequest(TokenRequest):
    password: Password


class SelectCarRequest(StrictRequest):
    user_car_id: UUID
