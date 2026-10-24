from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000


def split_text(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a reply into Telegram-safe chunks without breaking words."""
    text = (text or "").strip()
    if not text:
        return ["Готово."]
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        chunk = text[:cut].strip()
        if chunk:
            chunks.append(chunk)
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return chunks or ["Готово."]


async def answer_text(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Send a text reply, splitting it when Telegram would reject it."""
    chunks = split_text(text)
    for chunk in chunks[:-1]:
        await message.answer(chunk)
    await message.answer(chunks[-1], reply_markup=reply_markup)


async def edit_text_or_send(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Edit a message, but fall back to a new one when editing is impossible.

    Repeated taps produce «message is not modified»; old messages cannot be
    edited at all. Neither case should make a menu button stop working.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        logger.debug("message edit failed, sending a new one: %s", exc)
        await message.answer(text, reply_markup=reply_markup)


async def clear_markup(message: Message) -> None:
    try:
        await message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            logger.debug("cannot remove reply markup: %s", exc)
