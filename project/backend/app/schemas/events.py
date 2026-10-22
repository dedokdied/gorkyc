from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.event import EventSource as EventSource
from app.models.event import EventStatus as EventStatus
from app.models.event import EventType as EventType


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("invalid_timezone") from exc
    return value


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EventType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    due_at: AwareDatetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    timezone: str = "Europe/Moscow"
    recurrence: str | None = None

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title_must_not_be_empty")
        return normalized

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        return _validate_timezone(value)

    @model_validator(mode="after")
    def _validate_slots(self) -> "EventCreate":
        if self.type == EventType.meeting:
            if self.starts_at is None:
                raise ValueError("meeting_requires_starts_at")
            if self.ends_at is None and self.duration_minutes is None:
                raise ValueError("meeting_requires_ends_at_or_duration")
        if self.type == EventType.reminder and self.due_at is None:
            raise ValueError("reminder_requires_due_at")
        if self.starts_at is not None and self.ends_at is not None:
            if self.ends_at < self.starts_at:
                raise ValueError("ends_at_before_starts_at")
            if self.duration_minutes is not None:
                actual = int((self.ends_at - self.starts_at).total_seconds() // 60)
                if actual != self.duration_minutes:
                    raise ValueError("duration_mismatch")
        return self


class EventPatch(BaseModel):
    """Partial update.

    ``exclude_unset`` semantics are required: a missing field means "do not
    change", an explicit ``null`` means "clear". The service relies on
    ``model_fields_set`` to distinguish the two cases.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    due_at: AwareDatetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    timezone: str | None = None
    recurrence: str | None = None

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("title_must_not_be_empty")
        return normalized

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_timezone(value)

    @model_validator(mode="after")
    def _validate_patch(self) -> "EventPatch":
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title_must_not_be_null")
        if "timezone" in self.model_fields_set and self.timezone is None:
            raise ValueError("timezone_must_not_be_null")
        if self.starts_at is not None and self.ends_at is not None:
            if self.ends_at < self.starts_at:
                raise ValueError("ends_at_before_starts_at")
            if self.duration_minutes is not None:
                actual = int((self.ends_at - self.starts_at).total_seconds() // 60)
                if actual != self.duration_minutes:
                    raise ValueError("duration_mismatch")
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: EventType
    status: EventStatus
    title: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    due_at: datetime | None = None
    duration_minutes: int | None = None
    timezone: str = "Europe/Moscow"
    source: EventSource = EventSource.text
    recurrence: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class Period(BaseModel):
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None

    @model_validator(mode="after")
    def _validate_period(self) -> "Period":
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("period_end_before_start")
        return self
