from app.keyboards import clarification_keyboard


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
