from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventType as ModelEventType
from app.repositories.events import EventRepository
from app.schemas.search import SearchFilters, SearchHit, SearchRequest
from app.services.events import EventService


def _ensure_aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SearchService:
    async def search_events(self, user_id, query, filters=None):
        return await self.search(user_id, query, filters)

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EventRepository(db)

    async def search(self, user_id: UUID, query: Any = None, filters: Any = None, **kwargs) -> list[SearchHit]:
        # normalize filters
        ftype = None
        start = None
        end = None
        limit = 5
        if isinstance(filters, SearchFilters):
            ftype = filters.type
            start = _ensure_aware(filters.from_)
            end = _ensure_aware(filters.to)
            limit = filters.limit or 5
        elif isinstance(filters, dict):
            ftype = filters.get("type")
            start = _ensure_aware(filters.get("from_") or filters.get("from"))
            end = _ensure_aware(filters.get("to"))
            limit = filters.get("limit", 5) or 5
        elif filters is not None and hasattr(filters, "type"):
            ftype = getattr(filters, "type", None)
            start = _ensure_aware(getattr(filters, "from_", None) or getattr(filters, "from", None))
            end = _ensure_aware(getattr(filters, "to", None))
            limit = getattr(filters, "limit", None) or 5

        if isinstance(query, SearchRequest):
            req = query
            query = req.query
            if ftype is None:
                ftype = req.type
            if start is None:
                start = _ensure_aware(req.from_)
            if end is None:
                end = _ensure_aware(req.to)
            if limit == 5 and req.limit:
                limit = req.limit

        etype = None
        if ftype:
            try:
                etype = ModelEventType(ftype)
            except Exception:
                etype = None

        events = await self.repo.search(user_id, query or "", etype, start, end, limit)

        if kwargs:
            filters = dict(filters or {})
            filters.update(kwargs)
        hits = []
        for idx, ev in enumerate(events):
            # score: simple decreasing by position + similarity
            score = max(0.1, 1.0 - idx * 0.1)
            snippet = ev.search_text or ev.title
            if len(snippet) > 120:
                snippet = snippet[:120] + "..."
            read = EventService(self.db)._to_read(ev)
            hits.append(SearchHit(event=read, score=round(score, 2), snippet=snippet))
        return hits
