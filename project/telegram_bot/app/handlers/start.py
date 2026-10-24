from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import main_menu_keyboard, welcome_keyboard
from app.onboarding import CAPABILITIES, WELCOME
from app.state import clear_clarification

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await clear_clarification(state)
    data = await state.get_data()
    if data.get("onboarding_seen"):
        await message.answer(
            CAPABILITIES,
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        WELCOME,
        reply_markup=welcome_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await clear_clarification(state)
    await message.answer(
        CAPABILITIES,
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await clear_clarification(state)
    await message.answer(
        CAPABILITIES,
        reply_markup=main_menu_keyboard(),
    )
