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
)
from app.onboarding import CAPABILITIES, CREATE_HELP, EXAMPLES, PLANS

router = Router(name="onboarding")

PERIODS = {"today", "tomorrow", "week"}


async def _clear_clarification(state: FSMContext) -> None:
    await state.update_data(clarification_id=None, clarification_options=[])


@router.callback_query(F.data == "onboarding:start")
async def on_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _clear_clarification(state)
    await state.update_data(onboarding_seen=True)
    if callback.message:
        await callback.message.edit_text(
            CAPABILITIES,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "onboarding:examples")
async def on_examples(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _clear_clarification(state)
    await state.update_data(onboarding_seen=True)
    if callback.message:
        await callback.message.edit_text(
            EXAMPLES,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "onboarding:create")
async def on_create(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _clear_clarification(state)
    if callback.message:
        await callback.message.edit_text(
            CREATE_HELP,
            reply_markup=back_keyboard(),
        )


@router.callback_query(F.data == "onboarding:plans")
async def on_plans(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _clear_clarification(state)
    if callback.message:
        await callback.message.edit_text(
            PLANS,
            reply_markup=plans_keyboard(),
        )


@router.callback_query(F.data == "onboarding:back")
async def on_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _clear_clarification(state)
    if callback.message:
        await callback.message.edit_text(
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

    await callback.message.edit_reply_markup(reply_markup=None)
    await send_period(callback.message, state, api, settings, period)
