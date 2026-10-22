from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.events import EventRead, EventType


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: EventType | None = None
    from_: AwareDatetime | None = Field(default=None, alias="from")
    to: AwareDatetime | None = None
    limit: int = Field(default=5, ge=1, le=50)

    @model_validator(mode="after")
    def _validate_period(self) -> "SearchFilters":
        if self.from_ is not None and self.to is not None and self.to < self.from_:
            raise ValueError("period_end_before_start")
        return self


class SearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    type: EventType | None = None
    from_: AwareDatetime | None = Field(default=None, alias="from")
    to: AwareDatetime | None = None
    limit: int = Field(default=5, ge=1, le=50)

    @model_validator(mode="after")
    def _validate_period(self) -> "SearchRequest":
        if self.from_ is not None and self.to is not None and self.to < self.from_:
            raise ValueError("period_end_before_start")
        return self

    def to_filters(self) -> SearchFilters:
        return SearchFilters.model_validate(
            {"type": self.type, "from": self.from_, "to": self.to, "limit": self.limit}
        )


class SearchHit(BaseModel):
    event: EventRead
    score: float
    snippet: str


class SearchResponse(BaseModel):
    items: list[SearchHit]
