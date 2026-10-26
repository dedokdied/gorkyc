from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.chat import VoiceResponse
from app.services.voice import VoiceError, VoiceService

UserResolver = Callable[
    [int | None, str | None, str | None, str | None, str | None],
    Awaitable[str],
]
MAX_AUDIO_BYTES = 20 * 1024 * 1024


def build_voice_router(
    *,
    voice: VoiceService,
    resolve_user: UserResolver,
) -> APIRouter:
    router = APIRouter(tags=["voice"])

    @router.post("/voice", response_model=VoiceResponse)
    async def transcribe_voice(
        file: Annotated[UploadFile, File()],
        x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
        x_telegram_username: Annotated[
            str | None,
            Header(alias="X-Telegram-Username"),
        ] = None,
        x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
        x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        session_id: Annotated[str | None, Form()] = None,
        timezone: Annotated[str, Form()] = "Europe/Moscow",
        clarification_id: Annotated[str | None, Form()] = None,
    ) -> VoiceResponse | JSONResponse:
        user_id = await resolve_user(
            x_telegram_id,
            x_bot_secret,
            x_demo_user,
            x_telegram_username,
            authorization,
        )
        audio = await file.read()
        if len(audio) > MAX_AUDIO_BYTES:
            return _error(
                413,
                "audio_too_large",
                "Аудио больше 20 МБ. Отправь файл короче.",
            )

        try:
            result = await voice.handle(
                user_id,
                audio,
                file.filename or "voice.ogg",
                file.content_type or "audio/ogg",
                session_id=session_id or None,
                timezone=timezone,
                clarification_id=clarification_id or None,
            )
        except VoiceError as exc:
            return _error(400, exc.code, exc.user_message)

        return VoiceResponse(
            session_id=result.session_id,
            transcript=result.transcript,
            reply=result.reply,
            action=result.action,
            clarification=result.clarification,
            audio_url=result.audio_url,
        )

    return router


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
