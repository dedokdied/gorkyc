from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.message import Message
from app.models.session import Session
from app.services.dialogue import parse_uuid


class DbConversationStore:
    """Persist the dialogue in PostgreSQL so it survives restarts and reloads.

    The LLM only needs a short tail of the conversation, while the web client
    loads the full history through a separate query. Messages are keyed by
    session, and every session belongs to exactly one user.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | Callable[[], AsyncSession],
        max_messages: int = 12,
    ) -> None:
        self._session_factory = session_factory
        self._max_messages = max(2, max_messages)

    async def get(self, user_id: str, session_id: str) -> list[dict[str, str]]:
        uid = parse_uuid(user_id)
        sid = parse_uuid(session_id)
        if uid is None or sid is None:
            return []

        async with self._session_factory() as db:
            owner = await db.scalar(
                select(Session.user_id).where(Session.id == sid)
            )
            if owner != uid:
                return []
            rows = (
                await db.scalars(
                    select(Message)
                    .where(Message.session_id == sid)
                    .order_by(Message.created_at.desc(), Message.id.desc())
                    .limit(self._max_messages)
                )
            ).all()

        return [
            {"role": row.role, "content": row.content}
            for row in reversed(rows)
            if row.role in {"user", "assistant"} and row.content
        ]

    async def append(
        self,
        user_id: str,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        uid = parse_uuid(user_id)
        sid = parse_uuid(session_id)
        if uid is None or sid is None:
            return
        if not user_text.strip() or not assistant_text.strip():
            return

        async with self._session_factory() as db:
            session = await db.get(Session, sid)
            if session is None:
                session = Session(id=sid, user_id=uid)
                db.add(session)
                await db.flush()
            elif session.user_id is None:
                session.user_id = uid
            elif session.user_id != uid:
                return

            now = datetime.now(UTC)
            db.add_all(
                [
                    Message(
                        session_id=sid,
                        role="user",
                        content=user_text,
                        created_at=now,
                    ),
                    Message(
                        session_id=sid,
                        role="assistant",
                        content=assistant_text,
                        created_at=now + timedelta(microseconds=1),
                    ),
                ]
            )
            await db.commit()

    async def clear(self, user_id: str, session_id: str) -> None:
        uid = parse_uuid(user_id)
        sid = parse_uuid(session_id)
        if uid is None or sid is None:
            return

        async with self._session_factory() as db:
            owner = await db.scalar(
                select(Session.user_id).where(Session.id == sid)
            )
            if owner != uid:
                return
            await db.execute(delete(Message).where(Message.session_id == sid))
            await db.execute(delete(Session).where(Session.id == sid))
            await db.commit()


async def load_history(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str | None,
    limit: int = 500,
) -> list[dict[str, object]]:
    """Return the visible dialogue for one of the user's sessions."""

    sid = parse_uuid(session_id)
    if sid is None or user_id is None:
        return []

    owner = await db.scalar(select(Session.user_id).where(Session.id == sid))
    if owner != user_id:
        return []

    rows = (
        await db.scalars(
            select(Message)
            .where(Message.session_id == sid)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(limit)
        )
    ).all()

    return [
        {
            "id": str(row.id),
            "role": row.role,
            "content": row.content,
            "created_at": row.created_at,
        }
        for row in rows
        if row.role in {"user", "assistant"} and row.content
    ]
