from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal["task", "meeting", "reminder"]
EventPeriod = Literal["today", "tomorrow", "week", "upcoming", "all"]
Recurrence = Literal["daily", "weekly", "monthly"]


class CreateEventArgs(BaseModel):
    type: EventType
    title: str = Field(min_length=1, max_length=300)
    time_expression: str | None = None
    duration_expression: str | None = None
    description: str | None = None
    recurrence: Recurrence | None = None


class UpdateEventArgs(BaseModel):
    event_id: str
    title: str | None = Field(default=None, min_length=1, max_length=300)
    time_expression: str | None = None
    duration_expression: str | None = None
    description: str | None = None
    recurrence: Recurrence | None = None


class EventIdArgs(BaseModel):
    event_id: str


class ListEventsArgs(BaseModel):
    period: EventPeriod = "today"
    type: EventType | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SearchEventsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


class AskClarificationArgs(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(default_factory=list, max_length=5)
    missing: list[str] = Field(default_factory=list, max_length=5)


class GetCurrentDatetimeArgs(BaseModel):
    pass
