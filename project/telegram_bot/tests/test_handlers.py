from types import SimpleNamespace

from app.identity import user_id_from_message, username_from_user
from app.keyboards import (
    clarification_keyboard,
    main_menu_keyboard,
    plans_keyboard,
    welcome_keyboard,
)


def test_user_id_uses_account_id_instead_of_group_chat_id() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42, username="ivan"),
        chat=SimpleNamespace(id=-100123),
    )

    assert user_id_from_message(message) == 42
    assert username_from_user(message.from_user) == "@ivan"


def test_welcome_keyboard_has_start_and_examples() -> None:
    buttons = [button for row in welcome_keyboard().inline_keyboard for button in row]

    assert [button.text for button in buttons] == ["🚀 Начать", "💡 Примеры"]
    assert [button.callback_data for button in buttons] == [
        "onboarding:start",
        "onboarding:examples",
    ]


def test_main_menu_has_create_and_plans() -> None:
    buttons = [button for row in main_menu_keyboard().inline_keyboard for button in row]

    assert [button.text for button in buttons] == ["➕ Сделать задачу", "📅 Мои планы"]
    assert [button.callback_data for button in buttons] == [
        "onboarding:create",
        "onboarding:plans",
    ]


def test_plans_keyboard_has_periods_and_back() -> None:
    buttons = [button for row in plans_keyboard().inline_keyboard for button in row]

    assert [button.callback_data for button in buttons] == [
        "period:today",
        "period:tomorrow",
        "period:week",
        "onboarding:back",
    ]


def test_clarification_keyboard_builds_callback_data() -> None:
    markup = clarification_keyboard(
        {
            "id": "pending-1",
            "options": ["10:00", "15:00", "Выбрать"],
        }
    )

    assert markup is not None
    buttons = [button for row in markup.inline_keyboard for button in row]
    assert [button.text for button in buttons] == ["10:00", "15:00", "Выбрать"]
    assert [button.callback_data for button in buttons] == [
        "clarify:pending-1:0",
        "clarify:pending-1:1",
        "clarify:pending-1:2",
    ]


def test_clarification_keyboard_without_options_is_none() -> None:
    assert clarification_keyboard(None) is None
    assert clarification_keyboard({"id": "pending-1", "options": []}) is None
