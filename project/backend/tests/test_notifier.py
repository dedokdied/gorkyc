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
