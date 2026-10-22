from __future__ import annotations

import logging
from io import BytesIO

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.api_client import ApiClient, BackendError
from app.config import Settings
from app.handlers.text import send_chat_result

logger = logging.getLogger(__name__)
router = Router(name="voice")


@router.message(F.voice | F.audio)
async def on_voice(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
) -> None:
    media = message.voice or message.audio
    if media is None:
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    buffer = BytesIO()
    try:
        await message.bot.download(media.file_id, destination=buffer)
    except Exception:
        logger.exception("telegram file download failed")
        await message.answer("Не смог скачать голосовое. Попробуй ещё раз.")
        return

    if message.voice:
        filename = "voice.ogg"
        content_type = message.voice.mime_type or "audio/ogg"
    else:
        filename = message.audio.file_name or "audio.mp3"
        content_type = message.audio.mime_type or "audio/mpeg"

    data = await state.get_data()
    try:
        result = await api.voice(
            message.chat.id,
            buffer.getvalue(),
            filename,
            content_type,
            session_id=data.get("session_id"),
            timezone=data.get("timezone") or settings.app_tz,
        )
    except BackendError as exc:
        logger.warning("voice failed: %s", exc.code)
        await message.answer(exc.user_message)
        return

    await message.answer(f"Распознал: {result.transcript}")
    await send_chat_result(message, state, result.as_chat_result())
