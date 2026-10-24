from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import build_chat_router
from app.api.voice import build_voice_router
from app.integrations.stt import STTError
from app.schemas.chat import ActionInfo, ChatResponse
from app.services.voice import VoiceService

HEADERS = {
    "X-Telegram-Id": "42",
    "X-Bot-Secret": "test-secret",
}


class StubAssistant:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def handle(
        self,
        user_id: str,
        text: str,
        *,
        session_id: str | None = None,
        timezone: str = "Europe/Moscow",
    ) -> ChatResponse:
        self.calls.append(
            {
                "user_id": user_id,
                "text": text,
                "session_id": session_id,
                "timezone": timezone,
            }
        )
        if text == "уточнение":
            from app.schemas.chat import Clarification

            return ChatResponse(
                session_id="session-1",
                reply="Во сколько?",
                action=ActionInfo(
                    name="create_event",
                    status="needs_clarification",
                ),
                clarification=Clarification(
                    id="pending-1",
                    question="Во сколько?",
                    options=["10:00", "15:00"],
                ),
            )
        return ChatResponse(
            session_id="session-1",
            reply="Создал событие.",
            action=ActionInfo(name="create_event", entity_id="event-1"),
        )

    async def answer_clarification(
        self,
        user_id: str,
        clarification_id: str,
        text: str,
        *,
        session_id: str | None = None,
        timezone: str = "Europe/Moscow",
    ) -> ChatResponse:
        del user_id, timezone
        self.calls.append(
            {
                "clarification_id": clarification_id,
                "text": text,
                "session_id": session_id,
            }
        )
        return ChatResponse(
            session_id="session-1",
            reply="Готово: Встреча.",
            action=ActionInfo(name="create_event", entity_id="event-1"),
        )


class StubSTT:
    def __init__(self, text: str = "напомни завтра в 10") -> None:
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


def make_chat_client(assistant: StubAssistant) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_chat_router(
            assistant=assistant,  # type: ignore[arg-type]
            resolve_user=resolve_user,
        )
    )
    return TestClient(app)


async def resolve_user(
    telegram_id: int | None,
    secret: str | None,
    demo_user: str | None,
    telegram_username: str | None = None,
) -> str:
    del telegram_username
    if telegram_id is None:
        return demo_user or "demo"
    assert telegram_id == 42
    assert secret == "test-secret"
    return "user-1"


def test_chat_route_resolves_user_and_returns_response() -> None:
    assistant = StubAssistant()
    client = make_chat_client(assistant)

    response = client.post(
        "/chat",
        json={"text": "создай встречу", "timezone": "Europe/Moscow"},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Создал событие."
    assert assistant.calls[0]["user_id"] == "user-1"


def test_chat_route_allows_demo_user() -> None:
    assistant = StubAssistant()
    client = make_chat_client(assistant)

    response = client.post(
        "/chat",
        json={"text": "напомни встречу"},
        headers={"X-Demo-User": "alice"},
    )

    assert response.status_code == 200
    assert assistant.calls[0]["user_id"] == "alice"


def test_chat_route_defaults_to_demo_user() -> None:
    assistant = StubAssistant()
    client = make_chat_client(assistant)

    response = client.post("/chat", json={"text": "напомни встречу"})

    assert response.status_code == 200
    assert assistant.calls[0]["user_id"] == "demo"


def test_clarification_route_passes_answer() -> None:
    assistant = StubAssistant()
    client = make_chat_client(assistant)

    response = client.post(
        "/clarifications/pending-1/answer",
        json={"text": "15:00", "session_id": "session-1"},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Готово: Встреча."
    assert assistant.calls[0]["clarification_id"] == "pending-1"


def make_voice_client(stt: Any) -> TestClient:
    app = FastAPI()
    service = VoiceService(stt=stt, assistant=StubAssistant())  # type: ignore[arg-type]
    app.include_router(
        build_voice_router(
            voice=service,
            resolve_user=resolve_user,
        )
    )
    return TestClient(app)


def test_voice_route_transcribes_file_and_returns_text() -> None:
    stt = StubSTT()
    client = make_voice_client(stt)

    response = client.post(
        "/voice",
        files={"file": ("voice.ogg", b"ogg-bytes", "audio/ogg")},
        data={"session_id": "session-0", "timezone": "Europe/Moscow"},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "напомни завтра в 10"
    assert response.json()["reply"] == "Создал событие."
    assert stt.received == (b"ogg-bytes", "voice.ogg", "audio/ogg")


def test_voice_route_returns_contract_error() -> None:
    client = make_voice_client(FailingSTT())

    response = client.post(
        "/voice",
        files={"file": ("voice.ogg", b"ogg-bytes", "audio/ogg")},
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "stt_failed",
            "message": "Не удалось распознать голос. Напиши текстом.",
        }
    }
