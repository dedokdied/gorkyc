from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.pending_action import PendingAction as PendingActionRow
from app.services.dialogue import PendingAction, parse_uuid

_DEFAULT_TTL = timedelta(minutes=30)


class DbPendingActionStore:
    """Keep clarification questions in PostgreSQL.

    A pending action is scoped to a dialogue session. Only one action per
    session can be active at a time, which mirrors the single-question UX of
    both clients and lets an unfinished clarification survive a restart.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | Callable[[], AsyncSession],
        ttl: timedelta = _DEFAULT_TTL,
    ) -> None:
        self._session_factory = session_factory
        self._ttl = ttl

    async def save(self, action: PendingAction) -> None:
        aid = parse_uuid(action.id)
        uid = parse_uuid(action.user_id)
        if aid is None or uid is None or not action.session_id:
            return

        now = datetime.now(UTC)
        async with self._session_factory() as db:
            # The partial unique index allows only one active row per session.
            await db.execute(
                update(PendingActionRow)
                .where(
                    PendingActionRow.session_key == action.session_id,
                    PendingActionRow.id != aid,
                    PendingActionRow.is_active.is_(True),
                )
                .values(is_active=False, updated_at=now)
            )

            row = await db.get(PendingActionRow, aid)
            if row is None:
                row = PendingActionRow(id=aid)
                db.add(row)
            row.session_key = action.session_id
            row.user_id = uid
            row.intent = action.intent
            row.slots = action.args or {}
            row.missing = list(action.missing or [])
            row.question = action.question
            row.options = list(action.options or [])
            row.is_active = True
            row.expires_at = now + self._ttl
            row.updated_at = now
            await db.commit()

    async def get(self, action_id: str) -> PendingAction | None:
        aid = parse_uuid(action_id)
        if aid is None:
            return None

        async with self._session_factory() as db:
            row = await db.get(PendingActionRow, aid)
            if row is None or not row.is_active or row.expires_at <= datetime.now(UTC):
                return None
            return self._to_action(row)

    async def pop(self, action_id: str) -> PendingAction | None:
        aid = parse_uuid(action_id)
        if aid is None:
            return None

        async with self._session_factory() as db:
            row = await db.scalar(
                select(PendingActionRow)
                .where(PendingActionRow.id == aid)
                .with_for_update()
            )
            if row is None:
                return None
            expired = row.expires_at <= datetime.now(UTC)
            action = None if expired or not row.is_active else self._to_action(row)
            row.is_active = False
            row.updated_at = datetime.now(UTC)
            await db.commit()
            return action

    async def clear_session(self, user_id: str, session_id: str) -> None:
        uid = parse_uuid(user_id)
        sid = parse_uuid(session_id)
        if uid is None or sid is None:
            return
        async with self._session_factory() as db:
            await db.execute(
                delete(PendingActionRow).where(
                    PendingActionRow.session_key == str(sid),
                    PendingActionRow.user_id == uid,
                )
            )
            await db.commit()

    @staticmethod
    def _to_action(row: PendingActionRow) -> PendingAction:
        return PendingAction(
            id=str(row.id),
            user_id=str(row.user_id),
            session_id=row.session_key,
            intent=row.intent,
            args=dict(row.slots or {}),
            question=row.question or "",
            options=list(row.options or []),
            missing=list(row.missing or []),
        )
