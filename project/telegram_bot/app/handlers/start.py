from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api_client import ApiClient, BackendError
from app.config import Settings
from app.identity import user_id_from_message, username_from_user
from app.keyboards import main_menu_keyboard, welcome_keyboard
from app.onboarding import CAPABILITIES, WELCOME
from app.state import clear_clarification

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    api: ApiClient,
) -> None:
    await clear_clarification(state)
    user_id = user_id_from_message(message)
    username = username_from_user(message.from_user)
    try:
        profile = await api.get_me(user_id, telegram_username=username)
    except BackendError:
        profile = {}

    timezone = profile.get("timezone")
    if isinstance(timezone, str) and timezone:
        await state.update_data(timezone=timezone)

    if profile.get("onboarding_seen"):
        await message.answer(
            CAPABILITIES,
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        WELCOME,
        reply_markup=welcome_keyboard(),
    )
    try:
        await api.update_profile(
            user_id,
            onboarding_seen=True,
            telegram_username=username,
        )
    except BackendError:
        # A repeated /start is harmless; the next one retries the flag.
        pass


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


@router.message(Command("settings"))
async def cmd_settings(
    message: Message,
    state: FSMContext,
    api: ApiClient,
    settings: Settings,
    command: CommandObject,
) -> None:
    await clear_clarification(state)
    data = await state.get_data()
    current = data.get("timezone") or settings.app_tz
    requested = (command.args or "").strip()

    if not requested:
        await message.answer(
            f"Часовой пояс: <b>{current}</b>\n\n"
            "Чтобы изменить, отправь команду с зоной IANA, например:\n"
            "<code>/settings Europe/Moscow</code>\n"
            "<code>/settings Asia/Almaty</code>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        ZoneInfo(requested)
    except (ZoneInfoNotFoundError, ValueError):
        await message.answer(
            "Не знаю такую таймзону. Пример: Europe/Moscow, Asia/Almaty, UTC.",
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        await api.update_profile(
            user_id_from_message(message),
            timezone=requested,
            telegram_username=username_from_user(message.from_user),
        )
    except BackendError as exc:
        await message.answer(exc.user_message, reply_markup=main_menu_keyboard())
        return

    await state.update_data(timezone=requested)
    await message.answer(
        f"Сохранил часовой пояс: <b>{requested}</b>.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("link"))
async def cmd_link(
    message: Message,
    state: FSMContext,
    api: ApiClient,
) -> None:
    await clear_clarification(state)
    user_id = user_id_from_message(message)
    username = username_from_user(message.from_user)
    try:
        data = await api.create_link_code(user_id, telegram_username=username)
    except BackendError as exc:
        await message.answer(exc.user_message, reply_markup=main_menu_keyboard())
        return

    code = str(data.get("code") or "")
    if not code:
        await message.answer(
            "Не получилось создать код. Попробуйте ещё раз.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "Код для входа на сайт:\n\n"
        f"<b>{code}</b>\n\n"
        "Введите его в профиле на сайте. Код действует 10 минут.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
