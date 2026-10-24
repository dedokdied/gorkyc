from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.integrations.stt import (
    FasterWhisperSTT,
    OpenAIWhisperSTT,
    STTError,
    UnavailableSTT,
    build_stt_from_env,
)


def test_stt_defaults_to_api_when_key_is_set() -> None:
    config = Settings(
        _env_file=None,
        stt_provider="api",
        stt_api_key="test-key",
    )

    stt = build_stt_from_env(config)

    assert isinstance(stt, OpenAIWhisperSTT)


def test_stt_is_unavailable_without_api_key() -> None:
    config = Settings(
        _env_file=None,
        stt_provider="api",
        stt_api_key=None,
    )

    stt = build_stt_from_env(config)

    assert isinstance(stt, UnavailableSTT)


def test_stt_can_use_local_provider() -> None:
    config = Settings(
        _env_file=None,
        stt_provider="faster-whisper",
    )

    stt = build_stt_from_env(config)

    assert isinstance(stt, FasterWhisperSTT)


def test_stt_can_be_disabled() -> None:
    config = Settings(
        _env_file=None,
        stt_provider="none",
    )

    stt = build_stt_from_env(config)

    assert isinstance(stt, UnavailableSTT)


@pytest.mark.asyncio
async def test_openai_whisper_stt_calls_transcriptions_api() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = await request.aread()
        return httpx.Response(200, json={"text": "  купить хлеб  "})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        stt = OpenAIWhisperSTT(api_key="secret", client=client)

        text = await stt.transcribe(b"audio", "voice.ogg", "audio/ogg")

    assert text == "купить хлеб"
    assert str(captured["url"]).endswith("/audio/transcriptions")
    assert captured["auth"] == "Bearer secret"
    assert b"whisper-1" in captured["body"]
    assert b'name="language"' in captured["body"]
    assert b"ru" in captured["body"]


@pytest.mark.asyncio
async def test_openai_whisper_stt_raises_on_api_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        stt = OpenAIWhisperSTT(api_key="secret", client=client)

        with pytest.raises(STTError):
            await stt.transcribe(b"audio", "voice.ogg", "audio/ogg")
