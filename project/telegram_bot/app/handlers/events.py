from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User

from app.api_client import ApiClient, BackendError
from app.config import Settings
from app.formatting import format_events
from app.identity import user_id_from_message, username_from_user
from app.keyboards import with_main_menu
from app.state import clear_clarification
from app.time_ranges import local_range

logger = logging.getLogger(__name__)
router = Router(name="events")

PERIOD_TITLES = {
    "today": "Сегодня",
    "tomorrow": "Завтра",
    "week": "Ближайшие 7 дней",
}


@router.message(Command("today"))
async def cmd_today(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
) -> None:
    await send_period(message, state, api, settings, "today")


@router.message(Command("tomorrow"))
async def cmd_tomorrow(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
) -> None:
    await send_period(message, state, api, settings, "tomorrow")


@router.message(Command("week"))
async def cmd_week(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
) -> None:
    await send_period(message, state, api, settings, "week")


@router.message(Command("search"))
async def cmd_search(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
    command: CommandObject,
) -> None:
    await clear_clarification(state)
    query = (command.args or "").strip()
    if not query:
        await message.answer(
            "Напиши запрос: /search договор",
            reply_markup=with_main_menu(),
        )
        return
    if len(query) > 500:
        await message.answer(
            "Запрос слишком длинный. Сократи его до 500 символов.",
            reply_markup=with_main_menu(),
        )
        return

    data = await state.get_data()
    timezone = data.get("timezone") or settings.app_tz

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    try:
        events = await api.search_events(
            user_id_from_message(message),
            query,
            limit=5,
            telegram_username=username_from_user(message.from_user),
        )
    except BackendError as exc:
        logger.warning("search failed: %s", exc.code)
        await message.answer(exc.user_message, reply_markup=with_main_menu())
        return

    if not events:
        await message.answer(
            f"По запросу «{query}» ничего не нашёл.",
            reply_markup=with_main_menu(),
        )
        return

    body = format_events(events, timezone, limit=5)
    await message.answer(
        f"Результаты по «{query}»:\n\n{body}",
        reply_markup=with_main_menu(),
    )


async def send_period(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
    period: str,
    *,
    user: User | None = None,
) -> None:
    await clear_clarification(state)
    data = await state.get_data()
    timezone = data.get("timezone") or settings.app_tz
    start, end = local_range(period, timezone)
    # For inline callbacks message.from_user is the bot account. The caller
    # must pass callback.from_user explicitly, otherwise events are looked
    # up for the bot and the list is always empty.
    actor = user or message.from_user

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    try:
        events = await api.list_events(
            actor.id if actor is not None else message.chat.id,
            start=start.isoformat(),
            end=end.isoformat(),
            telegram_username=username_from_user(actor),
        )
    except BackendError as exc:
        logger.warning("list events failed: %s", exc.code)
        await message.answer(exc.user_message, reply_markup=with_main_menu())
        return

    body = format_events(events, timezone)
    await message.answer(
        f"{PERIOD_TITLES[period]}:\n\n{body}",
        reply_markup=with_main_menu(),
    )
