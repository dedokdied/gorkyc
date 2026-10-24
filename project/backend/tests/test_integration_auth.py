from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import (
    get_current_user_id,
    normalize_telegram_username,
    resolve_telegram_user,
)
from app.main import app


def test_telegram_username_is_normalized_for_display() -> None:
    assert normalize_telegram_username("@Ivan_42") == "Ivan_42"
    assert normalize_telegram_username("  @ivan ") == "ivan"
    assert normalize_telegram_username(None) is None
    assert normalize_telegram_username("bad name") is None


@pytest.mark.asyncio
async def test_bot_secret_is_rejected_before_db_access() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(
            x_telegram_id=42,
            x_telegram_username=None,
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


@pytest.mark.asyncio
async def test_resolve_api_user_demo_path_passes_explicit_empty_telegram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = uuid4()
    captured: dict[str, object] = {}

    @asynccontextmanager
    async def fake_session():
        yield object()

    async def fake_get_current_user_id(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(deps, "SessionLocal", fake_session)
    monkeypatch.setattr(deps, "get_current_user_id", fake_get_current_user_id)

    assert await deps.resolve_api_user(None, None, "alice") == expected
    assert captured["x_telegram_id"] is None
    assert captured["x_telegram_username"] is None
    assert captured["x_bot_secret"] is None
    assert captured["x_demo_user"] == "alice"


def test_cors_preflight_for_web_origin() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-demo-user",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
