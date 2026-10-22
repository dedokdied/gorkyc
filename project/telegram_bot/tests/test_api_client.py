import json

import httpx
import pytest

from app.api_client import ApiClient, BackendError
from app.config import Settings


def make_settings(**overrides: object) -> Settings:
    values = {
        "telegram_bot_token": "test-token",
        "backend_url": "http://test/api/v1",
        "bot_internal_secret": "test-secret",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.asyncio
async def test_chat_sends_telegram_headers_and_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "session_id": "session-1",
                "reply": "Создал напоминание",
                "action": {"name": "create_event", "status": "done"},
                "clarification": None,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=transport,
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        result = await api.chat(42, "напомни завтра", session_id=None)

    assert captured["path"] == "/api/v1/chat"
    headers = captured["headers"]
    assert headers["x-telegram-id"] == "42"
    assert headers["x-bot-secret"] == "test-secret"
    assert captured["payload"] == {
        "session_id": None,
        "text": "напомни завтра",
        "timezone": "Europe/Moscow",
    }
    assert result.session_id == "session-1"
    assert result.reply == "Создал напоминание"
    assert result.action == {"name": "create_event", "status": "done"}


@pytest.mark.asyncio
async def test_chat_maps_backend_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "error": {
                    "code": "validation_error",
                    "message": "Не понял время",
                }
            },
        )

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        with pytest.raises(BackendError) as exc_info:
            await api.chat(1, "когда-нибудь")

    assert exc_info.value.code == "validation_error"
    assert exc_info.value.user_message == "Не понял время"
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_chat_maps_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no backend", request=request)

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        with pytest.raises(BackendError) as exc_info:
            await api.chat(1, "привет")

    assert exc_info.value.code == "backend_unavailable"


@pytest.mark.asyncio
async def test_mock_mode_works_without_backend() -> None:
    api = ApiClient(make_settings(bot_mock_mode=True))
    try:
        result = await api.chat(7, "напомни завтра в 10 позвонить Ивану")
    finally:
        await api.close()

    assert result.session_id == "mock-7"
    assert "напоминание" in result.reply.lower()


@pytest.mark.asyncio
async def test_list_events_unwraps_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["status"] == "planned"
        return httpx.Response(
            200,
            json={
                "items": [
                    {"id": "event-1", "title": "Позвонить Ивану"},
                ]
            },
        )

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        events = await api.list_events(1, start="2026-10-23", end="2026-10-24")

    assert events == [{"id": "event-1", "title": "Позвонить Ивану"}]
