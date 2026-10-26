from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.event import Event, EventSource, EventStatus, EventType
from app.models.user import User
from app.services.events import EventService


@pytest.mark.asyncio
async def test_complete_recurring_reminder_creates_next_instance(db_session) -> None:
    user = User(
        id=uuid.uuid4(),
        openclaw_peer_id=f"telegram:{uuid.uuid4().int}",
        display_name="alice",
        timezone="Europe/Moscow",
    )
    db_session.add(user)
    await db_session.flush()

    due = datetime.now(UTC) + timedelta(hours=1)
    reminder = Event(
        user_id=user.id,
        type=EventType.reminder,
        status=EventStatus.planned,
        title="Пить воду",
        due_at=due,
        timezone="Europe/Moscow",
        source=EventSource.text,
        recurrence="daily",
        search_text="Пить воду",
        metadata_={},
    )
    db_session.add(reminder)
    await db_session.commit()

    await EventService(db_session).complete(user.id, reminder.id)

    rows = (
        await db_session.scalars(
            select(Event).where(Event.user_id == user.id).order_by(Event.created_at)
        )
    ).all()
    assert len(rows) == 2
    done = next(row for row in rows if row.id == reminder.id)
    follow_up = next(row for row in rows if row.id != reminder.id)
    assert done.status == EventStatus.done
    assert follow_up.status == EventStatus.planned
    assert follow_up.recurrence == "daily"
    assert follow_up.parent_id == reminder.id
    assert follow_up.due_at == due + timedelta(days=1)
