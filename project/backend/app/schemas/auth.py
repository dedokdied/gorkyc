from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not _EMAIL_RE.fullmatch(normalized):
        raise ValueError("invalid_email")
    if len(normalized) > 254:
        raise ValueError("email_too_long")
    return normalized


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("invalid_timezone") from exc
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)
    timezone: str = "Europe/Moscow"

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def _normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        return _validate_timezone(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        return _normalize_email(value)


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=100)
    timezone: str | None = None
    onboarding_seen: bool | None = None

    @field_validator("display_name")
    @classmethod
    def _normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name_must_not_be_empty")
        return normalized

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_timezone(value)


class AuthUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None = None
    display_name: str
    timezone: str
    created_at: datetime
    telegram_linked: bool = False
    telegram_username: str | None = None
    onboarding_seen: bool = False


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class LinkTelegramRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=5, max_length=5, pattern=r"^\d{5}$")
