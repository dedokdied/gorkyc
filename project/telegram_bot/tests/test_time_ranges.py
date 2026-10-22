from datetime import datetime
from zoneinfo import ZoneInfo

from app.time_ranges import local_range


def test_today_range_starts_at_midnight() -> None:
    now = datetime(2026, 10, 22, 18, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    start, end = local_range("today", "Europe/Moscow", now=now)

    assert start.isoformat() == "2026-10-22T00:00:00+03:00"
    assert end.isoformat() == "2026-10-23T00:00:00+03:00"


def test_tomorrow_range_is_next_day() -> None:
    now = datetime(2026, 10, 22, 18, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    start, end = local_range("tomorrow", "Europe/Moscow", now=now)

    assert start.isoformat() == "2026-10-23T00:00:00+03:00"
    assert end.isoformat() == "2026-10-24T00:00:00+03:00"


def test_week_range_is_seven_days() -> None:
    now = datetime(2026, 10, 22, 18, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    start, end = local_range("week", "Europe/Moscow", now=now)

    assert start.isoformat() == "2026-10-22T00:00:00+03:00"
    assert end.isoformat() == "2026-10-29T00:00:00+03:00"
