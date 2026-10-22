
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str | None = None
    text: str
    timezone: str = "Europe/Moscow"


class ChatResponse(BaseModel):
    session_id: str | None = None
    reply: str
    action: dict | None = None
    clarification: dict | None = None
    audio_url: str | None = None
