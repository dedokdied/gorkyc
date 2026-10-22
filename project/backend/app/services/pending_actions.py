from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pending_actions import PendingActionRepository


class PendingActionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PendingActionRepository(db)

    async def create(self, session_key: str, user_id: UUID, intent: str, slots=None, missing=None, last_entity_id=None):
        pa = await self.repo.create(session_key, user_id, intent, slots, missing, last_entity_id)
        await self.db.commit()
        return pa

    async def get_active(self, session_key: str):
        return await self.repo.get_active(session_key)

    async def deactivate(self, pending_action_id: UUID):
        await self.repo.deactivate(pending_action_id)
        await self.db.commit()

    async def resolve(self, session_key: str, slots: dict):
        pa = await self.repo.get_active(session_key)
        if pa is None:
            return None
        merged = dict(pa.slots or {})
        merged.update(slots or {})
        pa.slots = merged
        # update missing
        missing = [m for m in (pa.missing or []) if m not in merged]
        pa.missing = missing
        if not missing:
            pa.is_active = False
        await self.db.flush()
        await self.db.commit()
        return pa
