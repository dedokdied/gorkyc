from __future__ import annotations

import json

import httpx
import pytest

from app.integrations.telegram_notifier import (
    TelegramNotifier,
    TelegramNotifierError,
)


@pytest.mark.asyncio
async def test_notifier_sends_message_to_telegram() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        notifier = TelegramNotifier(token="123:abc", client=http_client)
        await notifier.send(42, "Пора на встречу")

    assert captured["path"] == "/bot123:abc/sendMessage"
    assert captured["payload"] == {
        "chat_id": 42,
        "text": "Пора на встречу",
        "disable_web_page_preview": True,
    }


@pytest.mark.asyncio
async def test_notifier_maps_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("telegram down", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        notifier = TelegramNotifier(token="123:abc", client=http_client)
        with pytest.raises(TelegramNotifierError):
            await notifier.send(42, "Пора на встречу")


@pytest.mark.asyncio
async def test_notifier_does_not_leak_token_in_status_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"ok": False, "description": "Bad Request: chat not found"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        notifier = TelegramNotifier(token="123:abc", client=http_client)
        with pytest.raises(TelegramNotifierError) as captured:
            await notifier.send(1, "Пора на встречу")

    message = str(captured.value)
    assert "chat not found" in message
    assert "123:abc" not in message
    assert captured.value.__cause__ is None
