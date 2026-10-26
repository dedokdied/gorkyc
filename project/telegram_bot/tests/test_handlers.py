from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.handlers import clarification, onboarding
from app.identity import user_id_from_message, username_from_user
from app.keyboards import (
    clarification_keyboard,
    main_menu_keyboard,
    plans_keyboard,
    welcome_keyboard,
    with_main_menu,
)
from app.messaging import split_text


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

    assert [button.text for button in buttons] == [
        "➕ Сделать задачу",
        "📅 Мои планы",
        "🔗 Связать с сайтом",
    ]
    assert [button.callback_data for button in buttons] == [
        "onboarding:create",
        "onboarding:plans",
        "link:code",
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


def test_main_menu_is_attached_to_every_reply() -> None:
    markup = with_main_menu()
    buttons = [button for row in markup.inline_keyboard for button in row]

    assert [button.callback_data for button in buttons] == [
        "onboarding:create",
        "onboarding:plans",
        "link:code",
    ]


def test_main_menu_keeps_clarification_options() -> None:
    markup = with_main_menu(
        clarification_keyboard({"id": "pending-1", "options": ["10:00", "15:00"]})
    )
    buttons = [button for row in markup.inline_keyboard for button in row]

    assert [button.callback_data for button in buttons] == [
        "clarify:pending-1:0",
        "clarify:pending-1:1",
        "onboarding:create",
        "onboarding:plans",
        "link:code",
    ]


@pytest.mark.asyncio
async def test_plan_period_uses_callback_user(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_send_period(message, state, api, settings, period, *, user=None):
        del message, state, api, settings
        captured["period"] = period
        captured["user"] = user

    monkeypatch.setattr(onboarding, "send_period", fake_send_period)

    callback = SimpleNamespace(
        data="period:today",
        from_user=SimpleNamespace(id=42, username="ivan"),
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
        answer=AsyncMock(),
    )

    await onboarding.on_period(
        callback,
        SimpleNamespace(),
        api=object(),
        settings=object(),
    )

    assert captured["period"] == "today"
    assert captured["user"].id == 42


@pytest.mark.asyncio
async def test_stale_clarification_button_is_rejected() -> None:
    callback = SimpleNamespace(
        data="clarify:pending-old:0",
        from_user=SimpleNamespace(id=42, username="ivan"),
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
        answer=AsyncMock(),
    )
    state = SimpleNamespace(
        get_data=AsyncMock(
            return_value={
                "clarification_id": "pending-new",
                "clarification_options": ["10:00"],
            }
        )
    )

    await clarification.on_clarification(
        callback,
        state,
        api=object(),
    )

    callback.answer.assert_awaited_once()
    assert "устарела" in callback.answer.await_args.args[0]
    callback.message.edit_reply_markup.assert_awaited_once_with(
        reply_markup=None
    )


def test_long_reply_is_split_without_losing_text() -> None:
    text = "слово " * 2000

    chunks = split_text(text, limit=100)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")
