from __future__ import annotations

import pytest

from app.integrations.stt import STTError
from app.schemas.chat import ActionInfo, ChatResponse
from app.services.voice import VoiceError, VoiceService


class FakeSTT:
    def __init__(self, text: str = "напомни завтра в 10 позвонить Ивану") -> None:
        self.text = text
        self.received: tuple[bytes, str, str] | None = None

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        self.received = (audio, filename, content_type)
        return self.text


class FailingSTT:
    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        del audio, filename, content_type
        raise STTError("provider failed")


class FakeAssistant:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None, str]] = []

    async def handle(
        self,
        user_id: str,
        text: str,
        *,
        session_id: str | None = None,
        timezone: str = "Europe/Moscow",
    ) -> ChatResponse:
        self.calls.append((user_id, text, session_id, timezone))
        return ChatResponse(
            session_id="session-1",
            reply="Создал напоминание.",
            action=ActionInfo(name="create_event", entity_id="event-1"),
        )


@pytest.mark.asyncio
async def test_voice_transcribes_and_passes_text_to_assistant() -> None:
    stt = FakeSTT()
    assistant = FakeAssistant()
    service = VoiceService(stt=stt, assistant=assistant)  # type: ignore[arg-type]

    result = await service.handle(
        "user-1",
        b"ogg-bytes",
        "voice.ogg",
        "audio/ogg",
        session_id="session-0",
    )

    assert stt.received == (b"ogg-bytes", "voice.ogg", "audio/ogg")
    assert assistant.calls == [
        ("user-1", stt.text, "session-0", "Europe/Moscow")
    ]
    assert result.transcript == stt.text
    assert result.reply == "Создал напоминание."
    assert result.action is not None
    assert result.action.entity_id == "event-1"


@pytest.mark.asyncio
async def test_voice_maps_stt_error_to_user_message() -> None:
    service = VoiceService(  # type: ignore[arg-type]
        stt=FailingSTT(),
        assistant=FakeAssistant(),
    )

    with pytest.raises(VoiceError) as exc_info:
        await service.handle("user-1", b"audio", "voice.ogg", "audio/ogg")

    assert exc_info.value.code == "stt_failed"
    assert "Напиши текстом" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_voice_rejects_empty_transcript() -> None:
    service = VoiceService(  # type: ignore[arg-type]
        stt=FakeSTT(text="   "),
        assistant=FakeAssistant(),
    )

    with pytest.raises(VoiceError) as exc_info:
        await service.handle("user-1", b"audio", "voice.ogg", "audio/ogg")

    assert exc_info.value.code == "stt_empty"
