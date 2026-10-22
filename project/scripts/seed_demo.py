"""Create a small, repeatable demo dataset for the web/Telegram demo user."""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.api.deps import resolve_api_user  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.models.event import Event, EventStatus  # noqa: E402
from app.services.events import ConflictError, EventService  # noqa: E402


@dataclass(frozen=True, slots=True)
class SeedEvent:
    event_type: str
    title: str
    days_from_today: int
    hour: int
    minute: int
    description: str | None = None
    done: bool = False


DEMO_EVENTS = (
    SeedEvent("reminder", "Позвонить Ивану", 1, 10, 0, "Обсудить договор"),
    SeedEvent("meeting", "Встреча с командой", 1, 15, 0, "Планирование недели"),
    SeedEvent("task", "Подготовить договор", 2, 12, 0, "Сверить условия с юристом"),
    SeedEvent("task", "Проверить почту", 5, 9, 0),
    SeedEvent("task", "Отправить счёт", -2, 18, 0, done=True),
)


async def run(args: argparse.Namespace) -> int:
    try:
        zone = ZoneInfo(args.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"неизвестная таймзона: {args.timezone}") from exc

    user_id = await resolve_api_user(None, None, args.user)
    created = skipped = conflicts = completed = 0

    for spec in DEMO_EVENTS:
        async with SessionLocal() as db:
            event = (
                await db.execute(
                    select(Event).where(
                        Event.user_id == user_id,
                        Event.title == spec.title,
                    )
                )
            ).scalar_one_or_none()

            if event is not None:
                skipped += 1
                if spec.done and event.status != EventStatus.done:
                    await EventService(db).complete(user_id, event.id)
                    completed += 1
                continue

            day = datetime.now(zone).date() + timedelta(days=spec.days_from_today)
            when = datetime.combine(day, time(spec.hour, spec.minute), tzinfo=zone)
            payload: dict = {
                "type": spec.event_type,
                "title": spec.title,
                "description": spec.description,
                "timezone": args.timezone,
            }
            if spec.event_type == "meeting":
                payload["starts_at"] = when
                payload["duration_minutes"] = 60
            else:
                payload["due_at"] = when

            try:
                event_read = await EventService(db).create(user_id, payload)
            except ConflictError:
                conflicts += 1
                print(f"пропуск (пересечение встреч): {spec.title}", file=sys.stderr)
                continue

            created += 1
            if spec.done:
                await EventService(db).complete(user_id, event_read.id)
                completed += 1

    print(
        f"user={args.user}: создано {created}, уже было {skipped}, "
        f"выполнено {completed}, конфликтов {conflicts}"
    )
    return 0 if conflicts == 0 else 1


async def amain() -> int:
    try:
        return await run(parse_args())
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo-событий")
    parser.add_argument("--user", default="demo", help="demo-user (X-Demo-User)")
    parser.add_argument("--timezone", default="Europe/Moscow")
    return parser.parse_args()


def main() -> int:
    try:
        return asyncio.run(amain())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
