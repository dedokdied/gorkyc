from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pending_action import PendingAction


class PendingActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_key: str,
        user_id: UUID,
        intent: str,
        slots: dict | None = None,
        missing: list | None = None,
        last_entity_id: UUID | None = None,
        expires_minutes: int = 30,
    ) -> PendingAction:
        # deactivate previous active
        await self.db.execute(
            update(PendingAction)
            .where(PendingAction.session_key == session_key, PendingAction.is_active.is_(True))
            .values(is_active=False)
        )
        pa = PendingAction(
            session_key=session_key,
            user_id=user_id,
            intent=intent,
            slots=slots or {},
            missing=missing or [],
            last_entity_id=last_entity_id,
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(minutes=expires_minutes),
        )
        self.db.add(pa)
        await self.db.flush()
        await self.db.refresh(pa)
        return pa

    async def get_active(self, session_key: str) -> PendingAction | None:
        stmt = (
            select(PendingAction)
            .where(
                PendingAction.session_key == session_key,
                PendingAction.is_active.is_(True),
                PendingAction.expires_at > datetime.now(UTC),
            )
            .order_by(PendingAction.created_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def deactivate(self, pending_action_id: UUID) -> None:
        await self.db.execute(
            update(PendingAction).where(PendingAction.id == pending_action_id).values(is_active=False)
        )
        await self.db.flush()

    async def list_by_session(self, session_key: str) -> list[PendingAction]:
        stmt = select(PendingAction).where(PendingAction.session_key == session_key).order_by(PendingAction.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
