from app.formatting import format_events


def test_format_events_converts_to_user_timezone() -> None:
    events = [
        {
            "type": "meeting",
            "title": "Встреча с Иваном",
            "starts_at": "2026-10-23T12:00:00Z",
        },
        {
            "type": "reminder",
            "title": "Позвонить Ивану",
            "due_at": "2026-10-23T07:00:00Z",
        },
    ]

    text = format_events(events, "Europe/Moscow")

    assert "Встреча: Встреча с Иваном (23.10 15:00)" in text
    assert "Напоминание: Позвонить Ивану (23.10 10:00)" in text


def test_format_events_empty() -> None:
    assert format_events([], "Europe/Moscow") == "Пока пусто."
