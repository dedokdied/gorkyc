from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventType as ModelEventType
from app.repositories.events import EventRepository
from app.schemas.search import SearchFilters, SearchHit, SearchRequest
from app.services.events import DomainValidationError, event_to_read


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EventRepository(db)

    async def search(
        self,
        user_id: UUID,
        query: str | None = None,
        filters: SearchFilters | SearchRequest | None = None,
    ) -> list[SearchHit]:
        if isinstance(filters, SearchRequest):
            filters = filters.to_filters()
        filters = filters or SearchFilters()

        normalized_query = (query or "").strip()
        if not normalized_query:
            raise DomainValidationError("query_required")

        start = filters.from_
        end = filters.to
        if start is not None and end is not None and end < start:
            raise DomainValidationError("period_end_before_start")

        event_type = None
        if filters.type is not None:
            value = filters.type.value if hasattr(filters.type, "value") else str(filters.type)
            event_type = ModelEventType(value)

        rows = await self.repo.search_with_scores(
            user_id=user_id,
            query=normalized_query,
            event_type=event_type,
            start=start,
            end=end,
            limit=filters.limit,
        )

        hits: list[SearchHit] = []
        for event, score in rows:
            snippet = (event.search_text or event.title or "").strip()
            if len(snippet) > 160:
                snippet = snippet[:160].rstrip() + "..."
            hits.append(
                SearchHit(
                    event=event_to_read(event),
                    score=round(float(score), 4),
                    snippet=snippet,
                )
            )
        return hits
