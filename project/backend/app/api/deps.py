import re
import secrets
import uuid
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import SessionLocal, get_db
from app.models.user import User

_TELEGRAM_USERNAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def normalize_telegram_username(value: str | None) -> str | None:
    """Return username without '@', or None if Telegram did not provide one.

    Telegram usernames are optional and can change. The numeric user id stays
    the canonical identity; the username is stored for display only.
    """
    if not isinstance(value, str):
        return None
    username = value.strip().lstrip("@").strip()
    if not username or not _TELEGRAM_USERNAME.fullmatch(username):
        return None
    return username


def _verify_bot_secret(secret: str | None) -> None:
    expected = settings.bot_internal_secret
    if not expected or not secrets.compare_digest(str(secret or ""), expected):
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "invalid_bot_secret"},
        )


async def get_current_user_id(
    x_demo_user: str | None = Header(default=None, alias="X-Demo-User", max_length=100),
    x_telegram_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    x_telegram_username: str | None = Header(
        default=None,
        alias="X-Telegram-Username",
        max_length=64,
    ),
    x_bot_secret: str | None = Header(default=None, alias="X-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    username = normalize_telegram_username(x_telegram_username)
    if x_telegram_id is not None:
        _verify_bot_secret(x_bot_secret)
        peer_id = f"telegram:{x_telegram_id}"
    else:
        peer_id = (x_demo_user or "demo").strip() or "demo"

    display_name = f"@{username}" if username else peer_id
    values = {
        "id": uuid.uuid4(),
        "openclaw_peer_id": peer_id,
        "display_name": display_name,
        "timezone": settings.app_tz,
    }

    # Idempotent upsert: safe under concurrent requests and doesn't create
    # duplicate users for the same Telegram account. If a username is known,
    # refresh display_name without touching the canonical peer id.
    if username:
        stmt = pg_insert(User).values(**values).on_conflict_do_update(
            index_elements=["openclaw_peer_id"],
            set_={"display_name": display_name},
        )
    else:
        stmt = pg_insert(User).values(**values).on_conflict_do_nothing(
            index_elements=["openclaw_peer_id"],
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


async def resolve_telegram_user(
    telegram_id: int,
    secret: str,
    username: str | None = None,
) -> UUID:
    _verify_bot_secret(secret)
    async with SessionLocal() as db:
        return await get_current_user_id(
            x_telegram_id=telegram_id,
            x_telegram_username=username,
            x_bot_secret=secret,
            db=db,
        )


async def resolve_api_user(
    telegram_id: int | None,
    secret: str | None,
    demo_user: str | None,
    telegram_username: str | None = None,
) -> UUID:
    if telegram_id is not None:
        return await resolve_telegram_user(
            telegram_id,
            secret or "",
            telegram_username,
        )

    async with SessionLocal() as db:
        return await get_current_user_id(
            x_telegram_id=None,
            x_telegram_username=None,
            x_bot_secret=None,
            x_demo_user=demo_user,
            db=db,
        )
