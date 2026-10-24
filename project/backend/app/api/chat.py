from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Header

from app.schemas.chat import ChatRequest, ChatResponse, ClarificationAnswer
from app.services.assistant import Assistant

UserResolver = Callable[
    [int | None, str | None, str | None, str | None],
    Awaitable[str],
]


def build_chat_router(
    *,
    assistant: Assistant,
    resolve_user: UserResolver,
) -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/chat", response_model=ChatResponse)
    async def chat(
        payload: ChatRequest,
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
    ) -> ChatResponse:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
        )
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
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
    ) -> ChatResponse:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
        )
        return await assistant.answer_clarification(
            user_id,
            clarification_id,
            payload.text,
            session_id=payload.session_id,
            timezone=payload.timezone,
        )

    return router
