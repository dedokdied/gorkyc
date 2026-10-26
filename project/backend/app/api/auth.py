from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models.event import Event
from app.models.pending_action import PendingAction
from app.models.session import Session
from app.models.telegram_link import TelegramLinkCode
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    AuthUser,
    LinkTelegramRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _unauthorized(message: str = "Неверный email или пароль.") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "invalid_credentials", "message": message},
    )


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=AuthUser.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    existing = await db.scalar(select(User.id).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "email_taken",
                "message": "Пользователь с таким email уже существует.",
            },
        )

    local_part = data.email.split("@", 1)[0]
    user = User(
        id=uuid.uuid4(),
        openclaw_peer_id=f"web:{uuid.uuid4()}",
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name or local_part,
        timezone=data.timezone,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "email_taken",
                "message": "Пользователь с таким email уже существует.",
            },
        ) from None

    await db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise _unauthorized()
    return _auth_response(user)


@router.get("/me", response_model=AuthUser)
async def me(user: User = Depends(get_current_user)) -> AuthUser:
    return AuthUser.model_validate(user)


@router.patch("/me", response_model=AuthUser)
async def update_me(
    data: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    fields = data.model_dump(exclude_unset=True)
    if "display_name" in fields and fields["display_name"] is not None:
        user.display_name = fields["display_name"]
    if "timezone" in fields and fields["timezone"] is not None:
        user.timezone = fields["timezone"]
    if "onboarding_seen" in fields and fields["onboarding_seen"] is not None:
        user.onboarding_seen = fields["onboarding_seen"]
    await db.commit()
    await db.refresh(user)
    return AuthUser.model_validate(user)


@router.post("/link-telegram", response_model=AuthUser)
async def link_telegram(
    data: LinkTelegramRequest,
    user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    """Bind the current web profile to the Telegram account that owns the code."""

    now = datetime.now(UTC)
    link = await db.scalar(
        select(TelegramLinkCode)
        .where(
            TelegramLinkCode.code == data.code,
            TelegramLinkCode.used_at.is_(None),
            TelegramLinkCode.expires_at > now,
        )
        .with_for_update()
    )
    if link is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_link_code", "message": "Код неверный или устарел."},
        )

    if user.telegram_id is not None and user.telegram_id != link.telegram_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "telegram_already_linked",
                "message": "К профилю уже привязан другой Telegram.",
            },
        )

    if user.telegram_id is None:
        existing = await db.scalar(
            select(User).where(
                User.telegram_id == link.telegram_id,
                User.id != user.id,
            )
        )
        if existing is None:
            existing = await db.scalar(
                select(User).where(
                    User.openclaw_peer_id == f"telegram:{link.telegram_id}",
                    User.id != user.id,
                )
            )

        if existing is not None:
            if existing.email:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "telegram_linked_elsewhere",
                        "message": "Этот Telegram уже привязан к другому профилю сайта.",
                    },
                )

            # A Telegram-only account already has events and history. Merge it
            # into the web account so both clients see one shared workspace.
            await db.execute(
                update(Event).where(Event.user_id == existing.id).values(user_id=user.id)
            )
            await db.execute(
                update(PendingAction)
                .where(PendingAction.user_id == existing.id)
                .values(user_id=user.id)
            )
            await db.execute(
                update(Session).where(Session.user_id == existing.id).values(user_id=user.id)
            )
            await db.delete(existing)
            await db.flush()

        user.telegram_id = link.telegram_id
        user.telegram_username = link.telegram_username

    link.used_at = now
    await db.commit()
    await db.refresh(user)
    return AuthUser.model_validate(user)


@router.post("/logout", status_code=204)
async def logout() -> Response:
    """The prototype uses stateless access tokens; the client drops its token.

    A real logout/revocation list belongs to the production auth iteration.
    """

    return Response(status_code=204)
