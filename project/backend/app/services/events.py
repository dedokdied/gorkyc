from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any, NoReturn
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventSource
from app.models.event import EventStatus as ModelEventStatus
from app.models.event import EventType as ModelEventType
from app.repositories.events import EventRepository
from app.schemas.events import (
    EventCreate,
    EventPatch,
    EventRead,
    EventStatus,
    EventType,
)


class NotFoundError(Exception):
    """Domain error: entity not found or belongs to another user."""


class ConflictError(Exception):
    """Domain error: state conflict (for example, meeting overlap)."""


class DomainValidationError(Exception):
    """Domain error: invalid input that could not be validated by a schema."""



def _uid(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise DomainValidationError("timezone_required")
    return value


def _build_search_text(title: str, description: str | None) -> str:
    parts = [title or ""]
    if description:
        parts.append(description)
    return " ".join(part for part in parts if part).strip()


def _minutes_between(starts_at: datetime, ends_at: datetime) -> int:
    return max(1, int((ends_at - starts_at).total_seconds() // 60))


def _as_create(data: EventCreate | dict | Any) -> EventCreate:
    if isinstance(data, EventCreate):
        return data
    if isinstance(data, dict):
        return EventCreate.model_validate(data)
    if hasattr(data, "model_dump"):
        return EventCreate.model_validate(data.model_dump())
    return EventCreate.model_validate(dict(data))


def _as_patch(data: EventPatch | dict | Any) -> EventPatch:
    if isinstance(data, EventPatch):
        return data
    if isinstance(data, dict):
        return EventPatch.model_validate(data)
    if hasattr(data, "model_dump"):
        return EventPatch.model_validate(data.model_dump(exclude_unset=True))
    return EventPatch.model_validate(dict(data))


def _raise_integrity_error(exc: IntegrityError) -> NoReturn:
    message = str(getattr(exc, "orig", exc)).lower()
    if "meetings_no_overlap" in message:
        raise ConflictError("meeting_overlap") from exc
    if "events_time_check" in message or "meetings_time_check" in message:
        raise DomainValidationError("invalid_time_range") from exc
    if "events_duration_check" in message:
        raise DomainValidationError("invalid_duration") from exc
    if "events_type_check" in message or "events_status_check" in message or "events_source_check" in message:
        raise DomainValidationError("invalid_event") from exc
    raise exc


def event_to_read(event: Event) -> EventRead:
    try:
        zone: tzinfo = ZoneInfo(event.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = UTC

    def local(value: datetime | None) -> datetime | None:
        return value.astimezone(zone) if value is not None else None

    return EventRead(
        id=event.id,
        type=EventType(event.type.value if hasattr(event.type, "value") else str(event.type)),
        status=EventStatus(event.status.value if hasattr(event.status, "value") else str(event.status)),
        title=event.title,
        description=event.description,
        starts_at=local(event.starts_at),
        ends_at=local(event.ends_at),
        due_at=local(event.due_at),
        duration_minutes=event.duration_minutes,
        timezone=event.timezone,
        source=EventSource(event.source.value if hasattr(event.source, "value") else str(event.source)),
        recurrence=event.recurrence,
        created_at=event.created_at,
        updated_at=event.updated_at,
        completed_at=event.completed_at,
    )


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EventRepository(db)

    async def create(self, user_id: UUID, data: EventCreate | dict | Any) -> EventRead:
        user_id = _uid(user_id)
        try:
            payload = _as_create(data)
        except PydanticValidationError as exc:
            raise DomainValidationError("invalid_event") from exc

        starts_at = _ensure_aware(payload.starts_at)
        ends_at = _ensure_aware(payload.ends_at)
        due_at = _ensure_aware(payload.due_at)
        duration = payload.duration_minutes
        event_type = payload.type

        if starts_at is not None and ends_at is None and duration is not None:
            ends_at = starts_at + timedelta(minutes=duration)
        if starts_at is not None and ends_at is not None and duration is None:
            duration = _minutes_between(starts_at, ends_at)

        if event_type == EventType.meeting:
            if starts_at is None:
                raise DomainValidationError("meeting_requires_starts_at")
            if ends_at is None:
                raise DomainValidationError("meeting_requires_ends_at_or_duration")
            if ends_at < starts_at:
                raise DomainValidationError("ends_at_before_starts_at")

        if event_type == EventType.reminder:
            if due_at is None:
                raise DomainValidationError("reminder_requires_due_at")
        elif event_type == EventType.task and due_at is None and starts_at is not None:
            due_at = starts_at

        if starts_at is not None and ends_at is not None and ends_at < starts_at:
            raise DomainValidationError("ends_at_before_starts_at")

        event = Event(
            user_id=user_id,
            type=ModelEventType(event_type.value),
            status=ModelEventStatus.planned,
            title=payload.title,
            description=payload.description,
            starts_at=starts_at,
            ends_at=ends_at,
            due_at=due_at,
            duration_minutes=duration,
            timezone=payload.timezone,
            source=EventSource.text,
            recurrence=payload.recurrence,
            search_text=_build_search_text(payload.title, payload.description),
            metadata_={},
        )

        if event.type == ModelEventType.meeting and event.starts_at and event.ends_at:
            if await self.repo.has_overlap(user_id, event.starts_at, event.ends_at):
                raise ConflictError("meeting_overlap")

        try:
            await self.repo.create(event)
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            _raise_integrity_error(exc)
        return event_to_read(event)

    async def get(self, user_id: UUID, event_id: UUID) -> EventRead:
        event = await self.repo.get(_uid(user_id), _uid(event_id))
        if event is None:
            raise NotFoundError("event_not_found")
        return event_to_read(event)

    async def update(self, user_id: UUID, event_id: UUID, data: EventPatch | dict | Any) -> EventRead:
        user_id = _uid(user_id)
        event = await self.repo.get(user_id, _uid(event_id))
        if event is None:
            raise NotFoundError("event_not_found")

        try:
            patch = _as_patch(data)
        except PydanticValidationError as exc:
            raise DomainValidationError("invalid_event") from exc
        fields = patch.model_dump(exclude_unset=True)

        new_title = fields.get("title", event.title)
        new_description = fields.get("description", event.description)
        new_timezone = fields.get("timezone", event.timezone)
        new_recurrence = fields.get("recurrence", event.recurrence)
        new_starts = _ensure_aware(fields["starts_at"]) if "starts_at" in fields else event.starts_at
        new_ends = _ensure_aware(fields["ends_at"]) if "ends_at" in fields else event.ends_at
        new_due = _ensure_aware(fields["due_at"]) if "due_at" in fields else event.due_at
        new_duration = fields.get("duration_minutes", event.duration_minutes)

        if new_title is None:
            raise DomainValidationError("title_must_not_be_null")
        if new_timezone is None:
            raise DomainValidationError("timezone_must_not_be_null")

        if event.type == ModelEventType.meeting:
            if new_starts is None:
                raise DomainValidationError("meeting_requires_starts_at")
            if "duration_minutes" in fields and new_duration is not None:
                new_ends = new_starts + timedelta(minutes=new_duration)
            elif "ends_at" in fields and new_ends is not None:
                new_duration = _minutes_between(new_starts, new_ends)
            elif "starts_at" in fields:
                if new_ends is not None and event.starts_at is not None and event.ends_at is not None:
                    old_duration = _minutes_between(event.starts_at, event.ends_at)
                    new_ends = new_starts + timedelta(minutes=old_duration)
                elif new_duration is not None:
                    new_ends = new_starts + timedelta(minutes=new_duration)
            elif new_ends is None and new_duration is not None:
                new_ends = new_starts + timedelta(minutes=new_duration)

            if new_ends is None:
                raise DomainValidationError("meeting_requires_ends_at_or_duration")
            if new_ends < new_starts:
                raise DomainValidationError("ends_at_before_starts_at")
            if new_duration is None:
                new_duration = _minutes_between(new_starts, new_ends)
        else:
            if new_starts is not None and new_ends is None and new_duration is not None:
                new_ends = new_starts + timedelta(minutes=new_duration)
            if new_starts is not None and new_ends is not None and new_duration is None:
                new_duration = _minutes_between(new_starts, new_ends)
            if new_starts is not None and new_ends is not None and new_ends < new_starts:
                raise DomainValidationError("ends_at_before_starts_at")

            if event.type == ModelEventType.reminder:
                if "due_at" in fields and new_due is None:
                    raise DomainValidationError("reminder_requires_due_at")
                if new_due is None:
                    if new_starts is not None:
                        new_due = new_starts
                    else:
                        raise DomainValidationError("reminder_requires_due_at")
            elif event.type == ModelEventType.task:
                if new_due is None and new_starts is not None and "due_at" not in fields:
                    new_due = new_starts

        # Проверяем пересечение до мутации ORM-объекта, чтобы не провоцировать
        # autoflush и не оставлять сессию в промежуточном состоянии.
        if event.type == ModelEventType.meeting and new_starts is not None and new_ends is not None:
            if await self.repo.has_overlap(user_id, new_starts, new_ends, exclude_id=event.id):
                raise ConflictError("meeting_overlap")

        event.title = new_title
        event.description = new_description
        event.timezone = new_timezone
        event.recurrence = new_recurrence
        event.starts_at = new_starts
        event.ends_at = new_ends
        event.due_at = new_due
        event.duration_minutes = new_duration
        event.search_text = _build_search_text(new_title, new_description)
        event.updated_at = datetime.now(UTC)

        try:
            await self.repo.update(event)
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            _raise_integrity_error(exc)
        return event_to_read(event)

    async def complete(self, user_id: UUID, event_id: UUID) -> EventRead:
        event = await self.repo.get(_uid(user_id), _uid(event_id))
        if event is None:
            raise NotFoundError("event_not_found")
        event.status = ModelEventStatus.done
        event.completed_at = datetime.now(UTC)
        event.updated_at = datetime.now(UTC)
        await self.repo.update(event)
        await self.db.commit()
        return event_to_read(event)

    async def delete(self, user_id: UUID, event_id: UUID) -> None:
        event = await self.repo.get(_uid(user_id), _uid(event_id))
        if event is None:
            raise NotFoundError("event_not_found")
        await self.repo.delete(event)
        await self.db.commit()

    async def list(
        self,
        user_id: UUID,
        period: Any = None,
        type: Any = None,
        start: Any = None,
        end: Any = None,
        from_: Any = None,
        to: Any = None,
    ) -> list[EventRead]:
        user_id = _uid(user_id)

        if period is not None:
            if hasattr(period, "start"):
                start = period.start
            if hasattr(period, "end"):
                end = period.end
            if isinstance(period, (tuple, list)) and len(period) >= 2:
                start, end = period[0], period[1]
            if isinstance(period, dict):
                start = period.get("start", period.get("from", start))
                end = period.get("end", period.get("to", end))
        if from_ is not None:
            start = from_
        if to is not None:
            end = to

        start = _ensure_aware(start)
        end = _ensure_aware(end)
        if start is not None and end is not None and end < start:
            raise DomainValidationError("period_end_before_start")

        event_type = None
        if type is not None:
            value = type.value if hasattr(type, "value") else str(type)
            event_type = ModelEventType(value)

        events = await self.repo.list_events(user_id, start, end, event_type)
        return [event_to_read(event) for event in events]
