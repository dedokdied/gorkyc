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
        result = await api.chat(
            42,
            "напомни завтра",
            session_id=None,
            telegram_username="@ivan",
        )

    assert captured["path"] == "/api/v1/chat"
    headers = captured["headers"]
    assert headers["x-telegram-id"] == "42"
    assert headers["x-telegram-username"] == "@ivan"
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
async def test_mock_events_can_be_filtered_by_period() -> None:
    api = ApiClient(make_settings(bot_mock_mode=True))
    try:
        all_events = await api.list_events(7)
        today_events = await api.list_events(
            7,
            start="2026-01-01T00:00:00+03:00",
            end="2026-01-02T00:00:00+03:00",
        )
    finally:
        await api.close()

    assert len(all_events) == 3
    assert today_events == []


@pytest.mark.asyncio
async def test_voice_sends_multipart_and_parses_transcript() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["content_type"] = request.headers["content-type"]
        captured["body"] = request.content
        return httpx.Response(
            200,
            json={
                "session_id": "session-1",
                "transcript": "напомни завтра в 10",
                "reply": "Создал напоминание.",
                "action": {"name": "create_event", "status": "done"},
                "clarification": None,
                "audio_url": None,
            },
        )

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        result = await api.voice(
            42,
            b"ogg-bytes",
            "voice.ogg",
            "audio/ogg",
            session_id="session-0",
        )

    assert captured["path"] == "/api/v1/voice"
    assert str(captured["content_type"]).startswith("multipart/form-data; boundary=")
    body = captured["body"]
    assert isinstance(body, bytes)
    assert b'name="file"; filename="voice.ogg"' in body
    assert b"ogg-bytes" in body
    assert b'name="session_id"' in body
    assert b"session-0" in body
    assert result.transcript == "напомни завтра в 10"
    assert result.reply == "Создал напоминание."
    assert result.as_chat_result().reply == "Создал напоминание."


@pytest.mark.asyncio
async def test_voice_passes_clarification_id() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(
            200,
            json={
                "session_id": "session-1",
                "transcript": "в час",
                "reply": "Готово: Встреча.",
                "action": {"name": "create_event", "status": "done"},
                "clarification": None,
                "audio_url": None,
            },
        )

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        await api.voice(
            42,
            b"ogg-bytes",
            "voice.ogg",
            "audio/ogg",
            clarification_id="pending-1",
        )

    body = captured["body"]
    assert isinstance(body, bytes)
    assert b'name="clarification_id"' in body
    assert b"pending-1" in body


@pytest.mark.asyncio
async def test_search_unwraps_event_hits() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "event": {
                            "id": "event-1",
                            "type": "task",
                            "title": "Проверить договор",
                        },
                        "score": 0.9,
                        "snippet": "Проверить договор",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        events = await api.search_events(1, "договор", limit=3)

    assert captured["payload"] == {"query": "договор", "limit": 3}
    assert events == [
        {"id": "event-1", "type": "task", "title": "Проверить договор"}
    ]


@pytest.mark.asyncio
async def test_mock_search_filters_events() -> None:
    api = ApiClient(make_settings(bot_mock_mode=True))
    try:
        events = await api.search_events(7, "договор")
    finally:
        await api.close()

    assert [event["title"] for event in events] == ["Подготовить договор"]


@pytest.mark.asyncio
async def test_list_events_unwraps_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "status" not in request.url.params
        return httpx.Response(
            200,
            json=[
                {"id": "event-1", "title": "Позвонить Ивану"},
            ],
        )

    async with httpx.AsyncClient(
        base_url="http://test/api/v1",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        api = ApiClient(make_settings(), http_client)
        events = await api.list_events(1, start="2026-10-23", end="2026-10-24")

    assert events == [{"id": "event-1", "title": "Позвонить Ивану"}]
