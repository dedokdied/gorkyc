from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User


async def get_current_user_id(
    x_demo_user: str | None = Header(default="demo", alias="X-Demo-User"),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    peer_id = x_demo_user or "demo"
    stmt = select(User).where(User.openclaw_peer_id == peer_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if user is None:
        # also try by display name / email? create new
        user = User(openclaw_peer_id=peer_id, display_name=peer_id, timezone="Europe/Moscow")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user.id


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="user_not_found")
    return user
