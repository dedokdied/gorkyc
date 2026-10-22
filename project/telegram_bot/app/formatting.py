from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TYPE_LABELS = {
    "task": "Задача",
    "meeting": "Встреча",
    "reminder": "Напоминание",
}
MAX_EVENTS = 20


def format_events(
    events: list[dict[str, Any]],
    timezone: str,
    *,
    limit: int = MAX_EVENTS,
) -> str:
    if not events:
        return "Пока пусто."

    lines = [format_event(event, timezone) for event in events[:limit]]
    if len(events) > limit:
        lines.append(f"… и ещё {len(events) - limit}")
    return "\n".join(lines)


def format_event(event: dict[str, Any], timezone: str) -> str:
    type_label = TYPE_LABELS.get(str(event.get("type")), "Событие")
    title = str(event.get("title") or "Без названия")
    when = event.get("starts_at") or event.get("due_at")
    when_text = format_moment(when, timezone)
    return f"— {type_label}: {title} ({when_text})"


def format_moment(value: Any, timezone: str) -> str:
    if not isinstance(value, str) or not value:
        return "без времени"

    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return "время не указано"

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(ZoneInfo(timezone)).strftime("%d.%m %H:%M")
