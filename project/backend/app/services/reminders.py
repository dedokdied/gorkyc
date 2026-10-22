from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.telegram_notifier import ReminderNotifier
from app.models.event import Event, EventStatus, EventType
from app.models.user import User

logger = get_logger("assistant.reminders")

_TELEGRAM_PREFIX = "telegram:"


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

    lines = [f"Напоминание: {event.title}"]
    if event.due_at is not None:
        local_due = event.due_at.astimezone(zone)
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
        sent = 0

        async with self._session_factory() as db:
            stmt = (
                select(Event, User.openclaw_peer_id)
                .join(User, User.id == Event.user_id)
                .where(
                    Event.type == EventType.reminder,
                    Event.status == EventStatus.planned,
                    Event.reminder_sent_at.is_(None),
                    Event.due_at.is_not(None),
                    Event.due_at <= moment,
                )
                .order_by(Event.due_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True, of=Event)
            )
            rows: list[Any] = list((await db.execute(stmt)).all())

            for event, peer_id in rows:
                telegram_id = telegram_id_from_peer(peer_id)
                if telegram_id is None:
                    logger.warning(
                        "reminder_without_telegram_user",
                        event_id=str(event.id),
                        peer_id=peer_id,
                    )
                    continue

                try:
                    await self._notifier.send(telegram_id, format_reminder(event))
                except Exception:
                    logger.exception(
                        "reminder_send_failed",
                        event_id=str(event.id),
                        telegram_id=telegram_id,
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
