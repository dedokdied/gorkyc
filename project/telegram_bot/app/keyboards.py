from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
