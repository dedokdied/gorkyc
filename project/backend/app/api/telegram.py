from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _verify_bot_secret, normalize_telegram_username
from app.db import get_db
from app.models.telegram_link import TelegramLinkCode

router = APIRouter(prefix="/telegram", tags=["telegram"])

LINK_CODE_TTL_SECONDS = 600


class LinkCodeResponse(BaseModel):
    code: str
    expires_in_seconds: int = LINK_CODE_TTL_SECONDS


@router.post("/link-code", response_model=LinkCodeResponse)
async def create_link_code(
    x_telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
    x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
    x_telegram_username: Annotated[
        str | None,
        Header(alias="X-Telegram-Username", max_length=64),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> LinkCodeResponse:
    _verify_bot_secret(x_bot_secret)
    if x_telegram_id <= 0:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_telegram_id", "message": "Некорректный Telegram ID."},
        )

    username = normalize_telegram_username(x_telegram_username)
    now = datetime.now(UTC)

    # Only one active code per Telegram account.
    await db.execute(
        delete(TelegramLinkCode).where(
            TelegramLinkCode.telegram_id == x_telegram_id,
            TelegramLinkCode.used_at.is_(None),
        )
    )

    code = ""
    for _ in range(20):
        candidate = f"{secrets.randbelow(100_000):05d}"
        exists = await db.scalar(
            select(TelegramLinkCode.id).where(TelegramLinkCode.code == candidate)
        )
        if exists is None:
            code = candidate
            break
    if not code:
        raise HTTPException(
            status_code=503,
            detail={"code": "code_generation_failed", "message": "Попробуйте ещё раз."},
        )

    db.add(
        TelegramLinkCode(
            code=code,
            telegram_id=x_telegram_id,
            telegram_username=username,
            expires_at=now + timedelta(seconds=LINK_CODE_TTL_SECONDS),
        )
    )
    await db.commit()
    return LinkCodeResponse(code=code)
