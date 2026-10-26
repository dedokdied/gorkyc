from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import (
    CYRILLIC_LOWER,
    CYRILLIC_UPPER,
    Event,
    EventStatus,
    EventType,
)


def _fold(column: Any):
    """Case-fold text in SQL independently of the database collation."""
    return func.lower(func.translate(column, CYRILLIC_UPPER, CYRILLIC_LOWER))


def _period_condition(start: Any | None, end: Any | None):
    """Return a SQL condition for events intersecting [start, end].

    Effective interval:
      start = coalesce(starts_at, due_at)
      end   = coalesce(ends_at, due_at, starts_at)

    Dateless events are excluded when a period is requested.
    """
    if start is None and end is None:
        return None

    effective_start = func.coalesce(Event.starts_at, Event.due_at)
    effective_end = func.coalesce(Event.ends_at, Event.due_at, Event.starts_at)
    conditions = [effective_start.is_not(None)]
    if start is not None:
        conditions.append(effective_end >= start)
    if end is not None:
        # Half-open period: an event at exactly 00:00 of the next day
        # belongs to the next day, not to the current one.
        conditions.append(effective_start < end)
    return and_(*conditions)


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, user_id: UUID, event_id: UUID) -> Event | None:
        stmt = select(Event).where(Event.id == event_id, Event.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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

    async def has_overlap(
        self,
        user_id: UUID,
        starts_at,
        ends_at,
        exclude_id: UUID | None = None,
    ) -> bool:
        if starts_at is None or ends_at is None:
            return False
        stmt = select(Event.id).where(
            Event.user_id == user_id,
            Event.type == EventType.meeting,
            Event.status == EventStatus.planned,
            Event.starts_at < ends_at,
            Event.ends_at > starts_at,
        )
        if exclude_id is not None:
            stmt = stmt.where(Event.id != exclude_id)
        result = await self.db.execute(stmt.limit(1))
        return result.first() is not None

    async def list_events(
        self,
        user_id: UUID,
        start: Any | None = None,
        end: Any | None = None,
        event_type: EventType | None = None,
        status: EventStatus | None = None,
    ) -> list[Event]:
        stmt = select(Event).where(Event.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(Event.type == event_type)
        if status is not None:
            stmt = stmt.where(Event.status == status)
        period_filter = _period_condition(start, end)
        if period_filter is not None:
            stmt = stmt.where(period_filter)
        stmt = stmt.order_by(
            Event.starts_at.asc().nulls_last(),
            Event.due_at.asc().nulls_last(),
            Event.created_at.desc(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _search_query(
        self,
        user_id: UUID,
        query: str,
        event_type: EventType | None,
        start: Any | None,
        end: Any | None,
        limit: int,
    ) -> Select:
        q = (query or "").strip().casefold()
        stmt = select(Event).where(Event.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(Event.type == event_type)
        period_filter = _period_condition(start, end)
        if period_filter is not None:
            stmt = stmt.where(period_filter)

        if not q:
            return stmt.order_by(Event.created_at.desc()).limit(limit)

        tsquery = func.plainto_tsquery("russian", q)
        rank = func.ts_rank_cd(Event.tsv, tsquery)
        similarity = func.similarity(_fold(Event.search_text), q)
        score = func.coalesce(rank, 0.0) * 0.7 + func.coalesce(similarity, 0.0) * 0.3
        like = f"%{q}%"

        stmt = stmt.where(
            or_(
                Event.tsv.op("@@")(tsquery),
                similarity > 0.05,
                _fold(Event.title).like(like),
                _fold(Event.description).like(like),
            )
        )
        return stmt.order_by(score.desc(), Event.created_at.desc()).limit(limit)

    async def search_with_scores(
        self,
        user_id: UUID,
        query: str,
        event_type: EventType | None = None,
        start: Any | None = None,
        end: Any | None = None,
        limit: int = 5,
    ) -> list[tuple[Event, float]]:
        q = (query or "").strip().casefold()
        if not q:
            stmt = self._search_query(user_id, q, event_type, start, end, limit)
            stmt = stmt.add_columns(literal(0.0).label("score"))
            result = await self.db.execute(stmt)
            return [(row[0], 0.0) for row in result.all()]

        tsquery = func.plainto_tsquery("russian", q)
        rank = func.coalesce(func.ts_rank_cd(Event.tsv, tsquery), 0.0)
        similarity = func.coalesce(func.similarity(_fold(Event.search_text), q), 0.0)
        score = (rank * 0.7 + similarity * 0.3).label("score")
        stmt = self._search_query(user_id, q, event_type, start, end, limit).add_columns(score)
        result = await self.db.execute(stmt)
        return [(row[0], float(row[1] or 0.0)) for row in result.all()]
