from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.api_client import ApiClient
from app.config import Settings
from app.handlers.events import send_period
from app.keyboards import (
    back_keyboard,
    main_menu_keyboard,
    plans_keyboard,
    with_main_menu,
)
from app.messaging import clear_markup, edit_text_or_send
from app.onboarding import CAPABILITIES, CREATE_HELP, EXAMPLES, PLANS
from app.state import clear_clarification

router = Router(name="onboarding")

PERIODS = {"today", "tomorrow", "week"}


@router.callback_query(F.data == "onboarding:start")
async def on_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_clarification(state)
    await state.update_data(onboarding_seen=True)
    if callback.message:
        await edit_text_or_send(
            callback.message,
            CAPABILITIES,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "onboarding:examples")
async def on_examples(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_clarification(state)
    await state.update_data(onboarding_seen=True)
    if callback.message:
        await edit_text_or_send(
            callback.message,
            EXAMPLES,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "onboarding:create")
async def on_create(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_clarification(state)
    if callback.message:
        await edit_text_or_send(
            callback.message,
            CREATE_HELP,
            reply_markup=with_main_menu(back_keyboard()),
        )


@router.callback_query(F.data == "onboarding:plans")
async def on_plans(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_clarification(state)
    if callback.message:
        await edit_text_or_send(
            callback.message,
            PLANS,
            reply_markup=with_main_menu(plans_keyboard()),
        )


@router.callback_query(F.data == "onboarding:back")
async def on_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_clarification(state)
    if callback.message:
        await edit_text_or_send(
            callback.message,
            CAPABILITIES,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("period:"))
async def on_period(
    callback: CallbackQuery,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
) -> None:
    await callback.answer()
    period = (callback.data or "").split(":", 1)[1]
    if period not in PERIODS or callback.message is None:
        return

    await clear_markup(callback.message)
    await send_period(
        callback.message,
        state,
        api,
        settings,
        period,
        user=callback.from_user,
    )
