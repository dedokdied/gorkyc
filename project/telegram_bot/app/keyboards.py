from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Начать",
                    callback_data="onboarding:start",
                ),
                InlineKeyboardButton(
                    text="💡 Примеры",
                    callback_data="onboarding:examples",
                ),
            ],
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Сделать задачу",
                    callback_data="onboarding:create",
                ),
                InlineKeyboardButton(
                    text="📅 Мои планы",
                    callback_data="onboarding:plans",
                ),
            ],
        ]
    )


def with_main_menu(
    markup: InlineKeyboardMarkup | None = None,
) -> InlineKeyboardMarkup:
    """Attach the main menu to any bot message.

    Inline keyboards live on a single message, so every new answer carries
    the menu again. Without this the buttons disappear as soon as the
    previous message is edited or pushed out of view.
    """
    rows = [list(row) for row in markup.inline_keyboard] if markup else []
    rows.extend(main_menu_keyboard().inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plans_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сегодня", callback_data="period:today"),
                InlineKeyboardButton(text="Завтра", callback_data="period:tomorrow"),
            ],
            [
                InlineKeyboardButton(text="Неделя", callback_data="period:week"),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="onboarding:back",
                ),
            ],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="onboarding:back",
                ),
            ],
        ]
    )


def clarification_keyboard(
    clarification: dict[str, Any] | None,
) -> InlineKeyboardMarkup | None:
    if not clarification:
        return None

    clarification_id = clarification.get("id")
    options = clarification.get("options") or []
    if not clarification_id or not options:
        return None

    buttons = [
        InlineKeyboardButton(
            text=str(option),
            callback_data=f"clarify:{clarification_id}:{index}",
        )
        for index, option in enumerate(options)
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)
