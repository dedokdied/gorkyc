import uuid
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.models.user import User


async def get_current_user_id(
    x_demo_user: str | None = Header(default="demo", alias="X-Demo-User", max_length=100),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    peer_id = (x_demo_user or "demo").strip() or "demo"

    # Idempotent upsert: safe under concurrent requests and doesn't create
    # duplicate users for the same OpenClaw peer.
    stmt = (
        pg_insert(User)
        .values(
            id=uuid.uuid4(),
            openclaw_peer_id=peer_id,
            display_name=peer_id,
            timezone=settings.app_tz,
        )
        .on_conflict_do_nothing(index_elements=["openclaw_peer_id"])
    )
    await db.execute(stmt)
    await db.commit()

    result = await db.execute(select(User).where(User.openclaw_peer_id == peer_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "user_not_found"},
        )
    return user.id


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "user_not_found"},
        )
    return user
