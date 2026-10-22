import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user_id, resolve_telegram_user


@pytest.mark.asyncio
async def test_bot_secret_is_rejected_before_db_access() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(
            x_telegram_id=42,
            x_bot_secret="wrong",
            db=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["message"] == "invalid_bot_secret"


@pytest.mark.asyncio
async def test_resolve_telegram_user_rejects_invalid_secret() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await resolve_telegram_user(42, "wrong")

    assert exc_info.value.status_code == 401
