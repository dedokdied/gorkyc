from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = None
    text: str = Field(min_length=1, max_length=4000)
    timezone: str = "Europe/Moscow"


class ClarificationAnswer(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class ActionInfo(BaseModel):
    name: str
    status: Literal["done", "needs_clarification", "failed"] = "done"
    entity_id: str | None = None


class Clarification(BaseModel):
    id: str
    question: str
    options: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    action: ActionInfo | None = None
    clarification: Clarification | None = None
    audio_url: str | None = None
