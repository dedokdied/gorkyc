from types import SimpleNamespace

from app.identity import user_id_from_message


def test_group_chat_uses_member_id_not_chat_id() -> None:
    """In a group chat.id is the group, so identity must come from from_user.id."""

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=1_000_001, username="alice"),
        chat=SimpleNamespace(id=-100_200_300),
    )
    assert user_id_from_message(message) == 1_000_001


def test_private_chat_still_uses_member_id() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42, username=None),
        chat=SimpleNamespace(id=42),
    )
    assert user_id_from_message(message) == 42
