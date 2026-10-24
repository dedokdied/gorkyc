from __future__ import annotations

from dataclasses import dataclass

from app.integrations.stt import STTClient, STTError
from app.schemas.chat import ActionInfo, Clarification
from app.services.assistant import Assistant


class VoiceError(Exception):
    def __init__(self, user_message: str, *, code: str = "voice_error") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.code = code


@dataclass(slots=True)
class VoiceResult:
    session_id: str
    transcript: str
    reply: str
    action: ActionInfo | None = None
    clarification: Clarification | None = None
    audio_url: str | None = None


class VoiceService:
    def __init__(self, *, stt: STTClient, assistant: Assistant) -> None:
        self._stt = stt
        self._assistant = assistant

    async def handle(
        self,
        user_id: str,
        audio: bytes,
        filename: str,
        content_type: str,
        *,
        session_id: str | None = None,
        timezone: str = "Europe/Moscow",
        clarification_id: str | None = None,
    ) -> VoiceResult:
        try:
            transcript = await self._stt.transcribe(audio, filename, content_type)
        except STTError as exc:
            raise VoiceError(
                "Не удалось распознать голос. Напиши текстом.",
                code="stt_failed",
            ) from exc

        transcript = transcript.strip()
        if not transcript:
            raise VoiceError(
                "Не разобрал речь. Попробуй ещё раз или напиши текстом.",
                code="stt_empty",
            )

        if clarification_id:
            response = await self._assistant.answer_clarification(
                user_id,
                clarification_id,
                transcript,
                session_id=session_id,
                timezone=timezone,
            )
        else:
            response = await self._assistant.handle(
                user_id,
                transcript,
                session_id=session_id,
                timezone=timezone,
            )
        return VoiceResult(
            session_id=response.session_id,
            transcript=transcript,
            reply=response.reply,
            action=response.action,
            clarification=response.clarification,
            audio_url=response.audio_url,
        )
