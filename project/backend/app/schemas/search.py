from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.events import EventRead


class SearchRequest(BaseModel):
    query: str
    type: str | None = None
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    limit: int = Field(default=5, ge=1, le=50)

    model_config = ConfigDict(populate_by_name=True)


class SearchFilters(BaseModel):
    type: str | None = None
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    limit: int = 5

    model_config = ConfigDict(populate_by_name=True)


class SearchHit(BaseModel):
    event: EventRead
    score: float
    snippet: str


class SearchResponse(BaseModel):
    items: list[SearchHit]
