from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.db import get_db
from app.models.event import Event, EventStatus, EventType
from app.schemas.events import EventRead
from app.services.events import NotFoundError, event_to_read

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/inbox", response_model=list[EventRead])
async def reminder_inbox(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[EventRead]:
    """Due events that the web client has not acknowledged yet.

    Telegram delivery is tracked separately with ``reminder_sent_at``: a user
    can receive the bot message and still see the in-app banner until they
    close it on the site. Tasks and meetings use their due/start time, just
    like the Telegram worker.
    """

    now = datetime.now(UTC)
    grace = timedelta(minutes=max(0, settings.reminders_grace_minutes))
    notify_at = func.coalesce(Event.due_at, Event.starts_at)
    rows = (
        await db.scalars(
            select(Event)
            .where(
                Event.user_id == user_id,
                Event.type.in_(
                    (EventType.task, EventType.meeting, EventType.reminder)
                ),
                Event.status == EventStatus.planned,
                notify_at.is_not(None),
                notify_at <= now,
                notify_at >= now - grace,
                Event.web_ack_at.is_(None),
            )
            .order_by(notify_at.asc())
            .limit(20)
        )
    ).all()
    return [event_to_read(event) for event in rows]


@router.post("/{event_id}/ack", response_model=EventRead)
async def acknowledge_reminder(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> EventRead:
    event = await db.scalar(
        select(Event).where(
            Event.id == event_id,
            Event.user_id == user_id,
            Event.type.in_(
                (EventType.task, EventType.meeting, EventType.reminder)
            ),
        )
    )
    if event is None:
        raise NotFoundError("reminder_not_found")
    event.web_ack_at = datetime.now(UTC)
    event.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(event)
    return event_to_read(event)
