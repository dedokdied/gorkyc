from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.event import Event, EventSource, EventStatus, EventType
from app.models.user import User
from app.services.events import EventService
from app.services.reminders import ReminderService, format_reminder, telegram_id_from_peer
from app.workers.reminders import ReminderWorker


class FakeNotifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[int, str]] = []

    async def send(self, telegram_id: int, text: str) -> None:
        if self.fail:
            raise RuntimeError("telegram unavailable")
        self.sent.append((telegram_id, text))


def _factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _create_reminder(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    peer_id: str = "telegram:42",
    due_at: datetime | None = None,
) -> uuid.UUID:
    async with session_factory() as db:
        user = User(
            id=uuid.uuid4(),
            openclaw_peer_id=peer_id,
            display_name=peer_id,
            timezone="Europe/Moscow",
        )
        db.add(user)
        await db.flush()
        event = Event(
            id=uuid.uuid4(),
            user_id=user.id,
            type=EventType.reminder,
            status=EventStatus.planned,
            title="Позвонить Ивану",
            description="Обсудить встречу",
            due_at=due_at or datetime.now(UTC) - timedelta(minutes=5),
            timezone="Europe/Moscow",
            source=EventSource.text,
            search_text="Позвонить Ивану Обсудить встречу",
            metadata_={},
        )
        db.add(event)
        await db.commit()
        return event.id


async def _create_notification_event(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    event_type: EventType,
    notify_at: datetime,
    telegram_id: int | None = None,
    peer_id: str = "telegram:42",
) -> uuid.UUID:
    async with session_factory() as db:
        user = User(
            id=uuid.uuid4(),
            openclaw_peer_id=peer_id,
            telegram_id=telegram_id,
            display_name=peer_id,
            timezone="Europe/Moscow",
        )
        db.add(user)
        await db.flush()
        event = Event(
            id=uuid.uuid4(),
            user_id=user.id,
            type=event_type,
            status=EventStatus.planned,
            title="Проверить уведомление",
            due_at=notify_at
            if event_type in {EventType.task, EventType.reminder}
            else None,
            starts_at=notify_at if event_type == EventType.meeting else None,
            ends_at=notify_at + timedelta(hours=1)
            if event_type == EventType.meeting
            else None,
            duration_minutes=60 if event_type == EventType.meeting else None,
            timezone="Europe/Moscow",
            source=EventSource.text,
            search_text="Проверить уведомление",
            metadata_={},
        )
        db.add(event)
        await db.commit()
        return event.id


@pytest.mark.asyncio
async def test_process_due_sends_reminder_once(db_engine) -> None:
    session_factory = _factory(db_engine)
    event_id = await _create_reminder(session_factory)
    notifier = FakeNotifier()

    sent = await ReminderService(session_factory, notifier).process_due()

    assert sent == 1
    assert notifier.sent[0][0] == 42
    assert "Позвонить Ивану" in notifier.sent[0][1]
    assert "Обсудить встречу" in notifier.sent[0][1]

    async with session_factory() as db:
        event = await db.get(Event, event_id)
        assert event is not None
        assert event.reminder_sent_at is not None

    assert await ReminderService(session_factory, notifier).process_due() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "label"),
    [(EventType.task, "Задача"), (EventType.meeting, "Встреча")],
)
async def test_process_due_sends_tasks_and_meetings(
    db_engine,
    event_type: EventType,
    label: str,
) -> None:
    session_factory = _factory(db_engine)
    due = datetime.now(UTC) - timedelta(seconds=30)
    await _create_notification_event(
        session_factory,
        event_type=event_type,
        notify_at=due,
        telegram_id=42,
    )
    notifier = FakeNotifier()

    assert await ReminderService(session_factory, notifier).process_due() == 1
    assert notifier.sent[0][0] == 42
    assert label in notifier.sent[0][1]


@pytest.mark.asyncio
async def test_stale_events_outside_grace_are_not_sent(db_engine) -> None:
    session_factory = _factory(db_engine)
    await _create_notification_event(
        session_factory,
        event_type=EventType.task,
        notify_at=datetime.now(UTC) - timedelta(hours=2),
        telegram_id=42,
    )
    notifier = FakeNotifier()

    assert await ReminderService(session_factory, notifier).process_due() == 0
    assert notifier.sent == []


@pytest.mark.asyncio
async def test_web_only_events_do_not_starve_telegram_delivery(db_engine) -> None:
    session_factory = _factory(db_engine)
    now = datetime.now(UTC)
    for index in range(5):
        await _create_notification_event(
            session_factory,
            event_type=EventType.reminder,
            notify_at=now - timedelta(minutes=5),
            peer_id=f"web:user-{index}",
        )
    await _create_notification_event(
        session_factory,
        event_type=EventType.reminder,
        notify_at=now,
        telegram_id=42,
    )
    notifier = FakeNotifier()

    assert await ReminderService(session_factory, notifier).process_due(limit=1) == 1
    assert notifier.sent[0][0] == 42


@pytest.mark.asyncio
async def test_failed_send_is_retried(db_engine) -> None:
    session_factory = _factory(db_engine)
    event_id = await _create_reminder(session_factory)

    sent = await ReminderService(session_factory, FakeNotifier(fail=True)).process_due()

    assert sent == 0
    async with session_factory() as db:
        event = await db.get(Event, event_id)
        assert event is not None
        assert event.reminder_sent_at is None


@pytest.mark.asyncio
async def test_future_reminder_is_not_sent(db_engine) -> None:
    session_factory = _factory(db_engine)
    await _create_reminder(
        session_factory,
        due_at=datetime.now(UTC) + timedelta(hours=1),
    )
    notifier = FakeNotifier()

    assert await ReminderService(session_factory, notifier).process_due() == 0
    assert notifier.sent == []


@pytest.mark.asyncio
async def test_non_telegram_user_is_skipped(db_engine) -> None:
    session_factory = _factory(db_engine)
    await _create_reminder(session_factory, peer_id="web:demo")
    notifier = FakeNotifier()

    assert await ReminderService(session_factory, notifier).process_due() == 0
    assert notifier.sent == []


def test_telegram_id_from_peer() -> None:
    assert telegram_id_from_peer("telegram:42") == 42
    assert telegram_id_from_peer("telegram:0") is None
    assert telegram_id_from_peer("telegram:abc") is None
    assert telegram_id_from_peer("web:demo") is None
    assert telegram_id_from_peer(None) is None


def test_format_reminder_uses_event_timezone() -> None:
    event = Event(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        type=EventType.reminder,
        status=EventStatus.planned,
        title="Позвонить",
        due_at=datetime(2026, 10, 23, 7, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
        source=EventSource.text,
        search_text="Позвонить",
        metadata_={},
    )

    text = format_reminder(event)

    assert "10:00" in text
    assert "23.10.2026" in text


@pytest.mark.asyncio
async def test_worker_runs_once_and_stops() -> None:
    class FakeService:
        def __init__(self) -> None:
            self.calls = 0

        async def process_due(self) -> int:
            self.calls += 1
            return 0

    service = FakeService()
    worker = ReminderWorker(service, interval_seconds=10)  # type: ignore[arg-type]

    worker.start()
    await asyncio.sleep(0.05)
    assert worker.running
    await worker.stop()

    assert service.calls == 1
    assert not worker.running

