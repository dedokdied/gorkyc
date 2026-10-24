from __future__ import annotations

from aiogram.types import Message, User


def user_id_from_message(message: Message) -> int:
    """Telegram account id, not chat id.

    In private chats they are equal, but in groups chat.id is the group id and
    would mix all members into one shared account.
    """
    if message.from_user is not None:
        return message.from_user.id
    return message.chat.id


def username_from_user(user: User | None) -> str | None:
    if user is None:
        return None
    username = (user.username or "").strip()
    return f"@{username}" if username else None
