from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.api_client import ApiClient, BackendError, ChatResult
from app.config import Settings
from app.identity import user_id_from_message, username_from_user
from app.keyboards import clarification_keyboard, with_main_menu
from app.messaging import answer_text
from app.state import clear_clarification

logger = logging.getLogger(__name__)
router = Router(name="text")

MAX_INPUT_LENGTH = 4000


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await clear_clarification(state)
    await message.answer(
        "Отменил уточнение. Напиши новый запрос.",
        reply_markup=with_main_menu(),
    )


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
    if len(text) > MAX_INPUT_LENGTH:
        await message.answer(
            f"Слишком длинное сообщение. Сократи его до {MAX_INPUT_LENGTH} символов.",
            reply_markup=with_main_menu(),
        )
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    data = await state.get_data()
    session_id = data.get("session_id")
    timezone = data.get("timezone") or settings.app_tz
    clarification_id = data.get("clarification_id")
    user_id = user_id_from_message(message)
    username = username_from_user(message.from_user)

    try:
        if clarification_id:
            result = await api.answer_clarification(
                user_id,
                str(clarification_id),
                text,
                session_id=session_id,
                timezone=timezone,
                telegram_username=username,
            )
            if "неактуально" in result.reply.lower():
                await state.update_data(
                    clarification_id=None,
                    clarification_options=[],
                )
                result = await api.chat(
                    user_id,
                    text,
                    session_id=session_id,
                    timezone=timezone,
                    telegram_username=username,
                )
        else:
            result = await api.chat(
                user_id,
                text,
                session_id=session_id,
                timezone=timezone,
                telegram_username=username,
            )
    except BackendError as exc:
        logger.warning("chat failed: %s", exc.code)
        await message.answer(exc.user_message, reply_markup=with_main_menu())
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

    await answer_text(
        message,
        reply,
        reply_markup=with_main_menu(clarification_keyboard(clarification)),
    )
