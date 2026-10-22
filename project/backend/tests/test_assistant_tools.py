import uuid

import pytest

from app.schemas.tools import CreateEventArgs
from app.services.assistant import ClarificationNeeded
from app.services.assistant_tools import DbToolExecutor, _as_uuid


@pytest.mark.asyncio
async def test_meeting_without_time_asks_for_time() -> None:
    executor = DbToolExecutor()

    with pytest.raises(ClarificationNeeded) as exc_info:
        await executor.create_event(
            "00000000-0000-0000-0000-000000000001",
            CreateEventArgs(
                type="meeting",
                title="Встреча с командой",
                time_expression="завтра",
            ),
            "Europe/Moscow",
        )

    assert exc_info.value.missing == ["starts_at"]


def test_period_week_starts_today() -> None:
    start, end = DbToolExecutor._period("week", "Europe/Moscow")

    assert start is not None
    assert end is not None
    assert (end - start).days == 7


def test_as_uuid_accepts_uuid_and_string() -> None:
    value = uuid.uuid4()

    assert _as_uuid(value) is value
    assert _as_uuid(str(value)) == value
