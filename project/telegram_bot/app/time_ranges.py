from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

PERIOD_DAYS = {
    "today": 1,
    "tomorrow": 1,
    "week": 7,
}
PERIOD_OFFSETS = {
    "today": 0,
    "tomorrow": 1,
    "week": 0,
}


def local_range(
    period: str,
    timezone: str,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    if period not in PERIOD_DAYS:
        raise ValueError(f"unknown period: {period}")

    zone = ZoneInfo(timezone)
    current = now or datetime.now(zone)
    if current.tzinfo is None:
        current = current.replace(tzinfo=zone)
    else:
        current = current.astimezone(zone)

    start_date = current.date() + timedelta(days=PERIOD_OFFSETS[period])
    end_date = start_date + timedelta(days=PERIOD_DAYS[period])
    start = datetime.combine(start_date, time.min, tzinfo=zone)
    end = datetime.combine(end_date, time.min, tzinfo=zone)
    return start, end
