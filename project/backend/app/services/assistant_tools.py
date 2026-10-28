from __future__ import annotations

import calendar
import re
from datetime import datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.db import SessionLocal
from app.schemas.events import EventRead
from app.schemas.search import SearchRequest
from app.schemas.tools import (
    CreateEventArgs,
    EventIdArgs,
    ListEventsArgs,
    SearchEventsArgs,
    UpdateEventArgs,
)
from app.services.assistant import ClarificationNeeded
from app.services.datetime_parser import DatetimeParser, ParsedTime
from app.services.events import (
    ConflictError,
    DomainValidationError,
    EventService,
    NotFoundError,
)
from app.services.search import SearchService

_EXPLICIT_TIME = re.compile(
    r"(?:\b(?:в|к)\s+\d{1,2}(?!\d)|\d{1,2}:\d{2}|\b\d{1,2}\s*"
    r"(?:час|часа|часов|утра|вечера|дня|ночи)\b|"
    r"\b(?:утром|днём|днем|вечером|ночью)\b|полдень|полночь)",
    re.IGNORECASE,
)

_ERROR_MESSAGES = {
    "meeting_overlap": "На это время уже есть встреча.",
    "event_not_found": "Событие не найдено.",
    "meeting_requires_starts_at": "Для встречи нужно указать дату и время.",
    "meeting_requires_ends_at_or_duration": "Укажи длительность встречи.",
    "reminder_requires_due_at": "Для напоминания нужно указать дату и время.",
    "period_end_before_start": "Конец периода раньше начала.",
}


def _error(code: str) -> dict[str, str]:
    return {"error": code, "message": _ERROR_MESSAGES.get(code, code)}


def _as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _zone(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("Europe/Moscow")


def _event_payload(event: EventRead) -> dict[str, Any]:
    return event.model_dump(mode="json")


class DbToolExecutor:
    def __init__(self, parser: DatetimeParser | None = None) -> None:
        self._parser = parser or DatetimeParser()

    def _parse(self, expression: str | None, timezone: str) -> ParsedTime | None:
        if not expression or not expression.strip():
            return None
        return self._parser.parse(expression, timezone)

    def _duration(
        self,
        parsed: ParsedTime | None,
        duration_expression: str | None,
        timezone: str,
    ) -> int | None:
        duration = self._parse(duration_expression, timezone)
        if duration is not None and duration.duration_minutes is not None:
            return duration.duration_minutes
        return parsed.duration_minutes if parsed is not None else None

    @staticmethod
    def _has_explicit_time(expression: str | None) -> bool:
        return bool(expression and _EXPLICIT_TIME.search(expression))

    @staticmethod
    def _needs_time(parsed: ParsedTime, expression: str | None) -> bool:
        return parsed.starts_at is not None and parsed.is_ambiguous and not DbToolExecutor._has_explicit_time(expression)

    @staticmethod
    def _next_recurring_start(
        parsed: ParsedTime,
        recurrence: str,
        timezone: str,
    ) -> ParsedTime:
        """Turn «в 9 утра» + recurrence into the next real occurrence.

        A recurring event needs a concrete first date: without one the row is
        saved dateless, and the assistant can truthfully say only «создано»,
        not when it starts. Use the next matching wall-clock time in the
        user's timezone.
        """
        if parsed.time is None:
            return parsed
        zone = _zone(timezone)
        now = datetime.now(zone)
        candidate = datetime.combine(now.date(), parsed.time, tzinfo=zone)
        if recurrence == "daily":
            while candidate <= now:
                candidate += timedelta(days=1)
        elif recurrence == "weekly":
            while candidate <= now:
                candidate += timedelta(days=7)
        elif recurrence == "monthly":
            while candidate <= now:
                year = candidate.year + (candidate.month // 12)
                month = candidate.month % 12 + 1
                day = min(candidate.day, calendar.monthrange(year, month)[1])
                candidate = candidate.replace(year=year, month=month, day=day)
        return ParsedTime(
            starts_at=candidate,
            due_at=candidate,
            date=candidate,
            time=parsed.time,
            duration_minutes=parsed.duration_minutes,
            is_ambiguous=False,
            confidence=parsed.confidence,
        )

    async def create_event(
        self,
        user_id: str,
        args: CreateEventArgs,
        timezone: str,
    ) -> dict[str, Any]:
        parsed = self._parse(args.time_expression, timezone)
        if (
            parsed is not None
            and args.recurrence is not None
            and parsed.date is None
            and parsed.time is not None
        ):
            parsed = self._next_recurring_start(parsed, args.recurrence, timezone)
        payload: dict[str, Any] = {
            "type": args.type,
            "title": args.title,
            "description": args.description,
            "timezone": timezone,
            "recurrence": args.recurrence,
        }

        if args.type == "meeting":
            if parsed is None or parsed.starts_at is None:
                raise ClarificationNeeded(
                    "На когда поставить встречу? Назови дату и время.",
                    missing=["starts_at"],
                )
            if self._needs_time(parsed, args.time_expression):
                raise ClarificationNeeded(
                    "Во сколько поставить встречу?",
                    missing=["starts_at"],
                )
            payload["starts_at"] = parsed.starts_at
            payload["duration_minutes"] = (
                self._duration(parsed, args.duration_expression, timezone) or 60
            )
        elif args.type == "reminder":
            if parsed is None or (parsed.due_at is None and parsed.starts_at is None):
                raise ClarificationNeeded(
                    "Когда напомнить? Назови дату и время.",
                    missing=["due_at"],
                )
            if self._needs_time(parsed, args.time_expression):
                raise ClarificationNeeded(
                    "Во сколько напомнить?",
                    missing=["due_at"],
                )
            payload["due_at"] = parsed.due_at or parsed.starts_at
        elif args.type == "task":
            # A task needs a concrete day and time. The spec does not define
            # a default 09:00, so never invent one: ask for the missing part.
            if parsed is None or (parsed.due_at is None and parsed.starts_at is None):
                raise ClarificationNeeded(
                    "На когда поставить задачу? Назови дату и время.",
                    missing=["due_at"],
                )
            if parsed.date is None and parsed.time is not None:
                raise ClarificationNeeded(
                    "На какой день поставить задачу?",
                    missing=["due_at"],
                )
            if self._needs_time(parsed, args.time_expression):
                raise ClarificationNeeded(
                    "Во сколько поставить задачу?",
                    missing=["due_at"],
                )
            payload["due_at"] = parsed.due_at or parsed.starts_at

        async with SessionLocal() as db:
            try:
                event = await EventService(db).create(_as_uuid(user_id), payload)
            except (ConflictError, DomainValidationError) as exc:
                return _error(str(exc))
        return _event_payload(event)

    async def update_event(
        self,
        user_id: str,
        args: UpdateEventArgs,
        timezone: str,
    ) -> dict[str, Any]:
        try:
            event_id = UUID(args.event_id)
        except ValueError:
            return _error("invalid_event_id")

        patch: dict[str, Any] = {}
        if args.title is not None:
            patch["title"] = args.title
        if args.description is not None:
            patch["description"] = args.description
        if args.recurrence is not None:
            patch["recurrence"] = args.recurrence

        parsed = self._parse(args.time_expression, timezone)
        if (
            parsed is not None
            and args.recurrence is not None
            and parsed.date is None
            and parsed.time is not None
        ):
            parsed = self._next_recurring_start(parsed, args.recurrence, timezone)
        if parsed is not None:
            if parsed.starts_at is not None:
                patch["starts_at"] = parsed.starts_at
            if parsed.due_at is not None:
                patch["due_at"] = parsed.due_at
            if parsed.ends_at is not None:
                patch["ends_at"] = parsed.ends_at

        duration = self._duration(parsed, args.duration_expression, timezone)
        if duration is not None:
            patch["duration_minutes"] = duration

        if not patch:
            return _error("nothing_to_update")

        async with SessionLocal() as db:
            try:
                event = await EventService(db).update(
                    _as_uuid(user_id),
                    event_id,
                    patch,
                )
            except (ConflictError, DomainValidationError, NotFoundError) as exc:
                return _error(str(exc))
        return _event_payload(event)

    async def complete_event(
        self,
        user_id: str,
        args: EventIdArgs,
        timezone: str,
    ) -> dict[str, Any]:
        del timezone
        try:
            event_id = UUID(args.event_id)
        except ValueError:
            return _error("invalid_event_id")

        async with SessionLocal() as db:
            try:
                event = await EventService(db).complete(_as_uuid(user_id), event_id)
            except NotFoundError as exc:
                return _error(str(exc))
        return _event_payload(event)

    async def delete_event(
        self,
        user_id: str,
        args: EventIdArgs,
        timezone: str,
    ) -> dict[str, Any]:
        del timezone
        try:
            event_id = UUID(args.event_id)
        except ValueError:
            return _error("invalid_event_id")

        async with SessionLocal() as db:
            try:
                await EventService(db).delete(_as_uuid(user_id), event_id)
            except NotFoundError as exc:
                return _error(str(exc))
        return {"deleted": True, "event_id": str(event_id)}

    async def list_events(
        self,
        user_id: str,
        args: ListEventsArgs,
        timezone: str,
    ) -> list[dict[str, Any]]:
        start, end = self._period(args.period, timezone)
        if args.date_from is not None or args.date_to is not None:
            first = args.date_from or args.date_to
            last = args.date_to or args.date_from
            if last < first:
                return [_error("period_end_before_start")]
            zone = _zone(timezone)
            start = datetime.combine(first, time.min, tzinfo=zone)
            end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=zone)
        async with SessionLocal() as db:
            try:
                events = await EventService(db).list(
                    _as_uuid(user_id),
                    start=start,
                    end=end,
                    type=args.type,
                    status="planned",
                )
            except DomainValidationError as exc:
                return [_error(str(exc))]
        return [_event_payload(event) for event in events[: args.limit]]

    async def search_events(
        self,
        user_id: str,
        args: SearchEventsArgs,
        timezone: str,
    ) -> list[dict[str, Any]]:
        del timezone
        request = SearchRequest(query=args.query, limit=args.limit)
        async with SessionLocal() as db:
            try:
                hits = await SearchService(db).search(
                    _as_uuid(user_id),
                    args.query,
                    request,
                )
            except DomainValidationError as exc:
                return [_error(str(exc))]
        return [hit.model_dump(mode="json") for hit in hits]

    @staticmethod
    def _period(period: str, timezone: str) -> tuple[datetime | None, datetime | None]:
        zone = _zone(timezone)
        today = datetime.now(zone).date()
        start_today = datetime.combine(today, time.min, tzinfo=zone)

        if period == "today":
            return start_today, start_today + timedelta(days=1)
        if period == "tomorrow":
            return start_today + timedelta(days=1), start_today + timedelta(days=2)
        if period == "week":
            # «Эта неделя» — текущая календарная неделя (пн–вс), а не
            # скользящие 7 дней: иначе в субботу ответ захватывает следующую
            # неделю и расходится с разбором «до конца недели».
            monday = start_today - timedelta(days=today.weekday())
            return monday, monday + timedelta(days=7)
        if period == "upcoming":
            return datetime.now(zone), start_today + timedelta(days=30)
        return None, None
