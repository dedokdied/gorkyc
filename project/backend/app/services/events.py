from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

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


def _ensure_aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _build_search_text(title: str, description: str | None) -> str:
    parts = [title or ""]
    if description:
        parts.append(description)
    return " ".join(p for p in parts if p).strip()


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ValidationError(Exception):
    pass


def _uid(v):
    from uuid import UUID
    if isinstance(v, UUID):
        return v
    return UUID(str(v))


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EventRepository(db)

    async def create(self, user_id: UUID, data: EventCreate | dict | Any) -> EventRead:
        user_id = _uid(user_id)
        if not isinstance(data, EventCreate):
            data = EventCreate(**(data if isinstance(data, dict) else data.model_dump() if hasattr(data, "model_dump") else dict(data)))

        starts_at = _ensure_aware(data.starts_at)
        ends_at = _ensure_aware(data.ends_at)
        due_at = _ensure_aware(data.due_at)
        duration = data.duration_minutes

        mtype = data.type.value if hasattr(data.type, "value") else str(data.type)

        if mtype == "meeting":
            if starts_at and duration and not ends_at:
                ends_at = starts_at + timedelta(minutes=duration)
            if not duration and starts_at and ends_at:
                duration = int((ends_at - starts_at).total_seconds() // 60)
        if mtype in ("task", "reminder"):
            if due_at is None and starts_at is not None:
                due_at = starts_at

        event = Event(
            user_id=user_id,
            type=ModelEventType(mtype),
            status=ModelEventStatus.planned,
            title=data.title,
            description=data.description,
            starts_at=starts_at,
            ends_at=ends_at,
            due_at=due_at,
            duration_minutes=duration,
            timezone=data.timezone or "Europe/Moscow",
            source=EventSource.text,
            recurrence=data.recurrence,
            search_text=_build_search_text(data.title, data.description),
            metadata_={},
        )
        # application-level overlap check for meetings
        if event.type == ModelEventType.meeting and event.starts_at and event.ends_at:
            if await self.repo.has_overlap(user_id, event.starts_at, event.ends_at):
                raise ConflictError("meeting_overlap")
        try:
            await self.repo.create(event)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("meeting_overlap")
        return self._to_read(event)

    async def get(self, user_id: UUID, event_id: UUID) -> EventRead:
        user_id = _uid(user_id)
        event = await self.repo.get(user_id, event_id)
        if event is None:
            raise NotFoundError("event_not_found")
        return self._to_read(event)

    async def update(self, user_id: UUID, event_id: UUID, data: EventPatch | dict | Any) -> EventRead:
        user_id = _uid(user_id)
        event = await self.repo.get(user_id, event_id)
        if event is None:
            raise NotFoundError("event_not_found")
        if not isinstance(data, EventPatch):
            data = EventPatch(**(data if isinstance(data, dict) else data.model_dump() if hasattr(data, "model_dump") else dict(data)))

        if data.title is not None:
            event.title = data.title
        if data.description is not None:
            event.description = data.description
        if data.timezone is not None:
            event.timezone = data.timezone
        if data.recurrence is not None:
            event.recurrence = data.recurrence
        if data.status is not None:
            event.status = ModelEventStatus(data.status.value if hasattr(data.status, "value") else str(data.status))
            if event.status == ModelEventStatus.done and event.completed_at is None:
                event.completed_at = datetime.now(UTC)
            if event.status != ModelEventStatus.done:
                event.completed_at = None

        new_starts = _ensure_aware(data.starts_at) if data.starts_at is not None else None
        new_ends = _ensure_aware(data.ends_at) if data.ends_at is not None else None
        new_due = _ensure_aware(data.due_at) if data.due_at is not None else None

        if data.starts_at is not None:
            event.starts_at = new_starts
        if data.ends_at is not None:
            event.ends_at = new_ends
        if data.due_at is not None:
            event.due_at = new_due
        if data.duration_minutes is not None:
            event.duration_minutes = data.duration_minutes

        # recompute ends for meetings
        if event.type == ModelEventType.meeting:
            if data.starts_at is not None and data.ends_at is None and data.duration_minutes is not None and event.starts_at:
                event.ends_at = event.starts_at + timedelta(minutes=data.duration_minutes)
            if event.starts_at and event.ends_at and data.duration_minutes is None:
                event.duration_minutes = int((event.ends_at - event.starts_at).total_seconds() // 60)

        event.search_text = _build_search_text(event.title, event.description)
        event.updated_at = datetime.now(UTC)
        if event.type == ModelEventType.meeting and event.starts_at and event.ends_at:
            if await self.repo.has_overlap(user_id, event.starts_at, event.ends_at, exclude_id=event.id):
                raise ConflictError("meeting_overlap")
        try:
            await self.repo.update(event)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("meeting_overlap")
        return self._to_read(event)

    async def complete(self, user_id: UUID, event_id: UUID) -> EventRead:
        user_id = _uid(user_id)
        event = await self.repo.get(user_id, event_id)
        if event is None:
            raise NotFoundError("event_not_found")
        event.status = ModelEventStatus.done
        event.completed_at = datetime.now(UTC)
        event.updated_at = datetime.now(UTC)
        await self.repo.update(event)
        await self.db.commit()
        return self._to_read(event)

    async def delete(self, user_id: UUID, event_id: UUID) -> None:
        user_id = _uid(user_id)
        event = await self.repo.get(user_id, event_id)
        if event is None:
            raise NotFoundError("event_not_found")
        await self.repo.delete(event)
        await self.db.commit()

    async def list(
        self,
        user_id: UUID,
        period: Any = None,
        type: Any = None,
        from_: Any = None,
        to: Any = None,
        **kwargs,
    ) -> list[EventRead]:
        user_id = _uid(user_id)
        # normalize period/from/to
        start = None
        end = None
        if period is not None:
            if hasattr(period, "start"):
                start = _ensure_aware(period.start)
            if hasattr(period, "end"):
                end = _ensure_aware(period.end)
            if isinstance(period, (tuple, list)) and len(period) >= 2:
                start = _ensure_aware(period[0])
                end = _ensure_aware(period[1])
            if isinstance(period, dict):
                start = _ensure_aware(period.get("start") or period.get("from"))
                end = _ensure_aware(period.get("end") or period.get("to"))
        if from_ is not None:
            start = _ensure_aware(from_)
        if to is not None:
            end = _ensure_aware(to)
        if "start" in kwargs:
            start = _ensure_aware(kwargs["start"])
        if "end" in kwargs:
            end = _ensure_aware(kwargs["end"])
        if "from" in kwargs:
            start = _ensure_aware(kwargs["from"])
        if "to" in kwargs and to is None:
            end = _ensure_aware(kwargs["to"])

        etype = None
        if type is not None:
            val = type.value if hasattr(type, "value") else str(type)
            etype = ModelEventType(val)

        events = await self.repo.list(user_id, start, end, etype)
        return [self._to_read(e) for e in events]

    async def get_list(self, user_id, **kwargs):
        return await self.list(user_id, **kwargs)

    # aliases for compatibility
    async def create_event(self, user_id, data):
        return await self.create(user_id, data)

    async def update_event(self, user_id, event_id, data):
        return await self.update(user_id, event_id, data)

    async def complete_event(self, user_id, event_id):
        return await self.complete(user_id, event_id)

    async def delete_event(self, user_id, event_id):
        return await self.delete(user_id, event_id)

    async def get_event(self, user_id, event_id):
        return await self.get(user_id, event_id)

    async def list_events(self, user_id, **kwargs):
        return await self.list(user_id, **kwargs)

    def _to_read(self, event: Event) -> EventRead:
        return EventRead(
            id=event.id,
            type=EventType(event.type.value if hasattr(event.type, "value") else str(event.type)),
            status=EventStatus(event.status.value if hasattr(event.status, "value") else str(event.status)),
            title=event.title,
            description=event.description,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            due_at=event.due_at,
            duration_minutes=event.duration_minutes,
            timezone=event.timezone,
            created_at=event.created_at,
            updated_at=event.updated_at,
            completed_at=event.completed_at,
        )
