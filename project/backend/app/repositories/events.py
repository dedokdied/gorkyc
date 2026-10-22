import builtins
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventType


class EventRepository:
    async def get_by_id(self, user_id, event_id):
        return await self.get(user_id, event_id)
    async def find_by_id(self, user_id, event_id):
        return await self.get(user_id, event_id)

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, user_id: UUID, event_id: UUID) -> Event | None:
        stmt = select(Event).where(Event.id == event_id, Event.user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, event: Event) -> Event:
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def update(self, event: Event) -> Event:
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete(self, event: Event) -> None:
        await self.db.delete(event)
        await self.db.flush()

    async def has_overlap(self, user_id: UUID, starts_at, ends_at, exclude_id=None) -> bool:
        stmt = select(Event).where(
            Event.user_id == user_id,
            Event.type == EventType.meeting,
            Event.status == "planned",
            Event.starts_at < ends_at,
            Event.ends_at > starts_at,
        )
        if exclude_id is not None:
            stmt = stmt.where(Event.id != exclude_id)
        res = await self.db.execute(stmt)
        return res.first() is not None

    async def list(
        self,
        user_id: UUID,
        start: Any | None = None,
        end: Any | None = None,
        event_type: EventType | None = None,
    ) -> list[Event]:
        stmt = select(Event).where(Event.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(Event.type == event_type)
        if start is not None:
            stmt = stmt.where(or_(Event.starts_at >= start, Event.due_at >= start, Event.starts_at.is_(None)))
        if end is not None:
            stmt = stmt.where(or_(Event.starts_at <= end, Event.due_at <= end, Event.starts_at.is_(None)))
        stmt = stmt.order_by(Event.starts_at.asc().nullslast(), Event.due_at.asc().nullslast(), Event.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def search(
        self,
        user_id: UUID,
        query: str,
        event_type: EventType | None = None,
        start: Any | None = None,
        end: Any | None = None,
        limit: int = 5,
    ) -> builtins.list[Event]:
        stmt = select(Event).where(Event.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(Event.type == event_type)
        if start is not None:
            stmt = stmt.where(or_(Event.starts_at >= start, Event.due_at >= start, Event.starts_at.is_(None)))
        if end is not None:
            stmt = stmt.where(or_(Event.starts_at <= end, Event.due_at <= end, Event.starts_at.is_(None)))
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    func.to_tsvector("russian", Event.search_text).op("@@")(func.plainto_tsquery("russian", q)),
                    func.similarity(Event.search_text, q) > 0.1,
                    Event.search_text.ilike(like),
                    Event.title.ilike(like),
                )
            )
        # ranking
        stmt = stmt.order_by(
            func.coalesce(func.ts_rank(func.to_tsvector("russian", Event.search_text), func.plainto_tsquery("russian", q)), 0).desc(),
            func.similarity(Event.search_text, q).desc(),
            Event.created_at.desc(),
        )
        stmt = stmt.limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
