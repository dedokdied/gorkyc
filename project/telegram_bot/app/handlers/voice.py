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
from app.identity import user_id_from_message, username_from_user
from app.keyboards import with_main_menu
from app.messaging import answer_text
from app.state import clear_clarification

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
        await message.answer(
            "Не смог скачать голосовое. Попробуй ещё раз.",
            reply_markup=with_main_menu(),
        )
        return

    if message.voice:
        filename = "voice.ogg"
        content_type = message.voice.mime_type or "audio/ogg"
    else:
        filename = message.audio.file_name or "audio.mp3"
        content_type = message.audio.mime_type or "audio/mpeg"

    data = await state.get_data()
    clarification_id = data.get("clarification_id")
    telegram_id = user_id_from_message(message)
    timezone = data.get("timezone") or settings.app_tz
    username = username_from_user(message.from_user)

    try:
        result = await api.voice(
            telegram_id,
            buffer.getvalue(),
            filename,
            content_type,
            session_id=data.get("session_id"),
            timezone=timezone,
            telegram_username=username,
            clarification_id=str(clarification_id) if clarification_id else None,
        )
        if clarification_id and "неактуально" in result.reply.lower():
            # The question expired while the voice message was being
            # transcribed. Treat the transcript as a new text request.
            await clear_clarification(state)
            chat_result = await api.chat(
                telegram_id,
                result.transcript,
                session_id=data.get("session_id"),
                timezone=timezone,
                telegram_username=username,
            )
        else:
            chat_result = result.as_chat_result()
    except BackendError as exc:
        logger.warning("voice failed: %s", exc.code)
        await message.answer(exc.user_message, reply_markup=with_main_menu())
        return

    await answer_text(
        message,
        f"Распознал: {result.transcript}",
        reply_markup=with_main_menu(),
    )
    await send_chat_result(message, state, chat_result)
