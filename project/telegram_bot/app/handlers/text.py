from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.api_client import ApiClient, BackendError, ChatResult
from app.config import Settings
from app.keyboards import clarification_keyboard

logger = logging.getLogger(__name__)
router = Router(name="text")


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    data = await state.get_data()
    session_id = data.get("session_id")

    try:
        result = await api.chat(
            message.chat.id,
            text,
            session_id=session_id,
            timezone=data.get("timezone") or settings.app_tz,
        )
    except BackendError as exc:
        logger.warning("chat failed: %s", exc.code)
        await message.answer(exc.user_message)
        return

    await send_chat_result(message, state, result)


async def send_chat_result(
    message: Message,
    state: FSMContext,
    result: ChatResult,
) -> None:
    if result.session_id:
        await state.update_data(session_id=result.session_id)

    clarification = result.clarification
    if clarification:
        options = clarification.get("options") or []
        await state.update_data(
            clarification_id=clarification.get("id"),
            clarification_options=[str(option) for option in options],
        )
    else:
        await state.update_data(
            clarification_id=None,
            clarification_options=[],
        )

    reply = result.reply
    if clarification and clarification.get("question"):
        question = str(clarification["question"])
        if question not in reply:
            reply = f"{reply}\n\n{question}" if reply else question

    await message.answer(
        reply,
        reply_markup=clarification_keyboard(clarification),
    )
