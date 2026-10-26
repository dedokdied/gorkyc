from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

from app.schemas.chat import (
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ClarificationAnswer,
)
from app.services.assistant import Assistant
from app.services.conversation_db import load_history
from app.services.dialogue import parse_uuid

UserResolver = Callable[
    [int | None, str | None, str | None, str | None, str | None],
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
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> ChatResponse:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
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
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> ChatResponse:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
        )
        return await assistant.answer_clarification(
            user_id,
            clarification_id,
            payload.text,
            session_id=payload.session_id,
            timezone=payload.timezone,
        )

    @router.get("/chat/history", response_model=list[ChatHistoryMessage])
    async def chat_history(
        session_id: str | None = Query(default=None),
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        db: AsyncSession = Depends(get_db),
    ) -> list[ChatHistoryMessage]:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
        )
        rows = await load_history(
            db,
            user_id=parse_uuid(user_id),
            session_id=session_id,
        )
        return [ChatHistoryMessage.model_validate(row) for row in rows]

    @router.delete("/chat/history", status_code=204)
    async def clear_chat_history(
        session_id: str | None = Query(default=None),
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> Response:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
        )
        await assistant.clear_history(user_id, session_id)
        return Response(status_code=204)

    @router.get("/sessions/{session_id}/messages", response_model=list[ChatHistoryMessage])
    async def session_messages(
        session_id: str,
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        db: AsyncSession = Depends(get_db),
    ) -> list[ChatHistoryMessage]:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
        )
        rows = await load_history(
            db,
            user_id=parse_uuid(user_id),
            session_id=session_id,
        )
        return [ChatHistoryMessage.model_validate(row) for row in rows]

    @router.delete("/sessions/{session_id}/messages", status_code=204)
    async def clear_session_messages(
        session_id: str,
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> Response:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
        )
        await assistant.clear_history(user_id, session_id)
        return Response(status_code=204)

    return router
