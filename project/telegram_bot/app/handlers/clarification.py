from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.api_client import ApiClient, BackendError
from app.handlers.text import send_chat_result
from app.identity import username_from_user

logger = logging.getLogger(__name__)
router = Router(name="clarification")


@router.callback_query(F.data.startswith("clarify:"))
async def on_clarification(
    callback: CallbackQuery,
    state: FSMContext,
    api: ApiClient,
) -> None:
    parts = (callback.data or "").split(":", 2)
    if len(parts) != 3:
        await callback.answer("Кнопка устарела. Напиши ответ текстом.", show_alert=True)
        return

    _, clarification_id, raw_index = parts
    try:
        index = int(raw_index)
    except ValueError:
        await callback.answer("Кнопка устарела. Напиши ответ текстом.", show_alert=True)
        return

    data = await state.get_data()
    options = data.get("clarification_options") or []
    if index >= len(options):
        await callback.answer("Кнопка устарела. Напиши ответ текстом.", show_alert=True)
        return

    answer = str(options[index])
    await callback.answer()

    telegram_id = callback.from_user.id
    try:
        result = await api.answer_clarification(
            telegram_id,
            clarification_id,
            answer,
            session_id=data.get("session_id"),
            timezone=data.get("timezone"),
            telegram_username=username_from_user(callback.from_user),
        )
    except BackendError as exc:
        logger.warning("clarification failed: %s", exc.code)
        if callback.message:
            await callback.message.answer(exc.user_message)
        return

    if callback.message:
        await send_chat_result(callback.message, state, result)
