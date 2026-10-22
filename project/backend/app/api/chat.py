from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Header

from app.schemas.chat import ChatRequest, ChatResponse, ClarificationAnswer
from app.services.assistant import Assistant

UserResolver = Callable[[int, str], Awaitable[str]]


def build_chat_router(
    *,
    assistant: Assistant,
    resolve_user: UserResolver,
) -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/chat", response_model=ChatResponse)
    async def chat(
        payload: ChatRequest,
        x_telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
        x_bot_secret: Annotated[str, Header(alias="X-Bot-Secret")],
    ) -> ChatResponse:
        user_id = await resolve_user(x_telegram_id, x_bot_secret)
        return await assistant.handle(
            user_id,
            payload.text,
            session_id=payload.session_id,
            timezone=payload.timezone,
        )

    @router.post(
        "/clarifications/{clarification_id}/answer",
        response_model=ChatResponse,
    )
    async def answer_clarification(
        clarification_id: str,
        payload: ClarificationAnswer,
        x_telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
        x_bot_secret: Annotated[str, Header(alias="X-Bot-Secret")],
    ) -> ChatResponse:
        user_id = await resolve_user(x_telegram_id, x_bot_secret)
        return await assistant.answer_clarification(
            user_id,
            clarification_id,
            payload.text,
            session_id=payload.session_id,
        )

    return router
