from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.telegram_notifier import ReminderNotifier
from app.models.event import Event, EventStatus, EventType
from app.models.user import User

logger = get_logger("assistant.reminders")

_TELEGRAM_PREFIX = "telegram:"
_TYPE_LABELS = {
    EventType.task: "Задача",
    EventType.meeting: "Встреча",
    EventType.reminder: "Напоминание",
}


def telegram_id_from_peer(peer_id: str | None) -> int | None:
    if not peer_id or not peer_id.startswith(_TELEGRAM_PREFIX):
        return None
    try:
        value = int(peer_id[len(_TELEGRAM_PREFIX) :])
    except ValueError:
        return None
    return value if value > 0 else None


def format_reminder(event: Event) -> str:
    timezone = event.timezone or settings.app_tz
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo(settings.app_tz)

    label = _TYPE_LABELS.get(event.type, "Напоминание")
    lines = [f"{label}: {event.title}"]
    moment = event.due_at or event.starts_at
    if moment is not None:
        local_due = moment.astimezone(zone)
        lines.append(f"Когда: {local_due:%d.%m.%Y %H:%M}")
    if event.description:
        lines.append(event.description)
    return "\n".join(lines)


class ReminderService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        notifier: ReminderNotifier,
    ) -> None:
        self._session_factory = session_factory
        self._notifier = notifier

    async def process_due(
        self,
        *,
        now: datetime | None = None,
        limit: int = 50,
    ) -> int:
        moment = now or datetime.now(UTC)
        grace = timedelta(minutes=max(0, settings.reminders_grace_minutes))
        notify_at = func.coalesce(Event.due_at, Event.starts_at)
        sent = 0

        async with self._session_factory() as db:
            stmt = (
                select(Event, User.openclaw_peer_id, User.telegram_id)
                .join(User, User.id == Event.user_id)
                .where(
                    Event.type.in_(
                        (EventType.task, EventType.meeting, EventType.reminder)
                    ),
                    Event.status == EventStatus.planned,
                    Event.reminder_sent_at.is_(None),
                    notify_at.is_not(None),
                    notify_at <= moment,
                    notify_at >= moment - grace,
                    # Web-only and demo users must not occupy the batch limit:
                    # otherwise their stale events can starve real deliveries.
                    or_(
                        User.telegram_id.is_not(None),
                        User.openclaw_peer_id.like(f"{_TELEGRAM_PREFIX}%"),
                    ),
                )
                .order_by(notify_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True, of=Event)
            )
            rows: list[Any] = list((await db.execute(stmt)).all())

            for event, peer_id, linked_telegram_id in rows:
                telegram_id = linked_telegram_id or telegram_id_from_peer(peer_id)
                if telegram_id is None:
                    logger.warning(
                        "reminder_without_telegram_user",
                        event_id=str(event.id),
                        peer_id=peer_id,
                    )
                    continue

                try:
                    await self._notifier.send(telegram_id, format_reminder(event))
                except Exception as exc:
                    # The notifier message is sanitized: HTTP errors must not
                    # carry the Telegram URL with the bot token into logs.
                    logger.error(
                        "reminder_send_failed",
                        event_id=str(event.id),
                        telegram_id=telegram_id,
                        error=str(exc),
                    )
                    continue

                event.reminder_sent_at = moment
                sent += 1
                logger.info(
                    "reminder_sent",
                    event_id=str(event.id),
                    telegram_id=telegram_id,
                )

            await db.commit()

        return sent
