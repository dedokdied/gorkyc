import uuid
from datetime import datetime

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


@pytest.mark.asyncio
async def test_task_with_date_but_without_time_asks_for_time() -> None:
    executor = DbToolExecutor()

    with pytest.raises(ClarificationNeeded) as exc_info:
        await executor.create_event(
            "00000000-0000-0000-0000-000000000001",
            CreateEventArgs(
                type="task",
                title="Поесть",
                time_expression="в пятницу",
            ),
            "Europe/Moscow",
        )

    assert exc_info.value.question == "Во сколько поставить задачу?"
    assert exc_info.value.missing == ["due_at"]


@pytest.mark.asyncio
async def test_task_without_date_asks_for_date_and_time() -> None:
    executor = DbToolExecutor()

    with pytest.raises(ClarificationNeeded) as exc_info:
        await executor.create_event(
            "00000000-0000-0000-0000-000000000001",
            CreateEventArgs(type="task", title="Поесть"),
            "Europe/Moscow",
        )

    assert exc_info.value.question == "На когда поставить задачу? Назови дату и время."
    assert exc_info.value.missing == ["due_at"]


def test_period_week_is_current_calendar_week() -> None:
    start, end = DbToolExecutor._period("week", "Europe/Moscow")

    assert start is not None
    assert end is not None
    assert start.weekday() == 0  # Monday
    assert (end - start).days == 7
    assert start.date() <= datetime.now(start.tzinfo).date() < end.date()


def test_as_uuid_accepts_uuid_and_string() -> None:
    value = uuid.uuid4()

    assert _as_uuid(value) is value
    assert _as_uuid(str(value)) == value
