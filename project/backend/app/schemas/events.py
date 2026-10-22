from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventStatus as EventStatus
from app.models.event import EventType as EventType


class EventCreate(BaseModel):
    type: EventType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    due_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    timezone: str = "Europe/Moscow"
    recurrence: str | None = None


class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    due_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    timezone: str | None = None
    recurrence: str | None = None
    status: EventStatus | None = None


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
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class Period(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
