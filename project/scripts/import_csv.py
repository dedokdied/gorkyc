"""Import the demo event corpus from CSV into PostgreSQL.

The dataset is a seed/search corpus, not real user data. Rows are classified
as meeting, reminder or task and imported with source="import".
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.api.deps import resolve_api_user  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.models.event import Event, EventSource  # noqa: E402
from app.services.events import ConflictError, DomainValidationError, EventService  # noqa: E402

MEETING_WORDS = re.compile(r"(встреч|созвон|план[её]рк|демо)", re.IGNORECASE)
REMINDER_WORDS = re.compile(r"напомн", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CsvEvent:
    row: int
    title: str
    event_type: str
    when: datetime


def classify(text: str) -> str:
    if MEETING_WORDS.search(text):
        return "meeting"
    if REMINDER_WORDS.search(text):
        return "reminder"
    return "task"


def find_default_csv() -> Path:
    for directory in (PROJECT_ROOT / "data", REPO_ROOT):
        matches = sorted(directory.glob("voice_assistant_events_1000_*.csv"))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        "CSV не найден; передай путь аргументом --csv "
        "или положи voice_assistant_events_1000_*.csv в project/data"
    )


def parse_rows(path: Path, timezone: str) -> list[CsvEvent]:
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"неизвестная таймзона: {timezone}") from exc

    events: list[CsvEvent] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"date", "time", "text"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"в CSV нет колонок: {', '.join(sorted(missing))}")

        for row_number, row in enumerate(reader, start=2):
            title = (row.get("text") or "").strip()
            if not title:
                raise ValueError(f"строка {row_number}: пустой текст")
            if len(title) > 300:
                raise ValueError(f"строка {row_number}: текст длиннее 300 символов")

            try:
                event_date = date.fromisoformat((row.get("date") or "").strip())
                event_time = time.fromisoformat((row.get("time") or "").strip())
            except ValueError as exc:
                raise ValueError(
                    f"строка {row_number}: неверные дата/время "
                    f"{(row.get('date'), row.get('time'))}"
                ) from exc

            events.append(
                CsvEvent(
                    row=row_number,
                    title=title,
                    event_type=classify(title),
                    when=datetime.combine(event_date, event_time, tzinfo=zone),
                )
            )
    return events


def payload_for(item: CsvEvent, timezone: str, meeting_duration: int) -> dict:
    payload: dict = {
        "type": item.event_type,
        "title": item.title,
        "timezone": timezone,
    }
    if item.event_type == "meeting":
        payload["starts_at"] = item.when
        payload["duration_minutes"] = meeting_duration
    else:
        payload["due_at"] = item.when
    return payload


async def existing_keys(user_id) -> set[tuple[str, datetime]]:
    async with SessionLocal() as db:
        result = await db.execute(
            select(Event.title, Event.starts_at, Event.due_at).where(
                Event.user_id == user_id,
                Event.source == EventSource.import_,
            )
        )
        return {
            (title, starts_at or due_at)
            for title, starts_at, due_at in result.all()
            if starts_at or due_at
        }


async def run(args: argparse.Namespace) -> int:
    if args.meeting_duration <= 0:
        raise ValueError("--meeting-duration должен быть больше нуля")
    path = args.csv or find_default_csv()
    events = parse_rows(path, args.timezone)

    unique: list[CsvEvent] = []
    seen: set[tuple[str, datetime]] = set()
    for item in events:
        key = (item.title, item.when)
        if args.dedupe:
            if key in seen:
                continue
            seen.add(key)
        unique.append(item)

    counts = {"meeting": 0, "reminder": 0, "task": 0}
    for item in unique:
        counts[item.event_type] += 1

    print(
        f"CSV: {path}\n"
        f"строк: {len(events)}, к импорту: {len(unique)} "
        f"(встречи {counts['meeting']}, напоминания {counts['reminder']}, "
        f"задачи {counts['task']})"
    )

    if args.dry_run:
        print("dry-run: БД не изменялась")
        return 0

    user_id = await resolve_api_user(None, None, args.user)
    known = await existing_keys(user_id) if args.dedupe else set()

    imported = skipped = conflicts = 0
    for item in unique:
        key = (item.title, item.when)
        if key in known:
            skipped += 1
            continue

        async with SessionLocal() as db:
            try:
                await EventService(db).create(
                    user_id,
                    payload_for(item, args.timezone, args.meeting_duration),
                    source=EventSource.import_,
                )
            except (ConflictError, DomainValidationError) as exc:
                print(
                    f"строка {item.row}: {item.when.isoformat()} "
                    f"«{item.title}» пропущена ({exc})",
                    file=sys.stderr,
                )
                conflicts += 1
                continue

        known.add(key)
        imported += 1

    print(
        f"user={args.user}: импортировано {imported}, "
        f"дублей {skipped}, конфликтов {conflicts}"
    )
    return 0 if conflicts == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Импорт CSV-корпуса в БД")
    parser.add_argument("--csv", type=Path, help="путь к CSV (utf-8-sig)")
    parser.add_argument("--user", default="demo", help="demo-user (X-Demo-User)")
    parser.add_argument(
        "--timezone",
        default="Europe/Moscow",
        help="таймзона дат из CSV",
    )
    parser.add_argument(
        "--meeting-duration",
        type=int,
        default=15,
        help="длительность импортируемых встреч в минутах (по умолчанию 15, "
        "чтобы соседние слоты корпуса не пересекались)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="только проверить и посчитать строки",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_false",
        dest="dedupe",
        help="импортировать дубли внутри CSV",
    )
    parser.set_defaults(dedupe=True)
    return parser.parse_args()


async def amain() -> int:
    try:
        return await run(parse_args())
    finally:
        await engine.dispose()


def main() -> int:
    try:
        return asyncio.run(amain())
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
