from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import time as dtime
from zoneinfo import ZoneInfo

import dateparser


@dataclass
class ParsedTime:
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    due_at: datetime | None = None
    duration_minutes: int | None = None
    date: datetime | None = None
    time: dtime | None = None
    is_ambiguous: bool = False
    confidence: float = 1.0

    # aliases
    @property
    def start(self):
        return self.starts_at

    @property
    def end(self):
        return self.ends_at

    @property
    def due(self):
        return self.due_at

    @property
    def start_at(self):
        return self.starts_at

    @property
    def end_at(self):
        return self.ends_at

    @property
    def due_date(self):
        return self.due_at

    @property
    def dt(self):
        return self.starts_at or self.due_at


def _to_aware(dt, tz):
    if dt is None:
        return None
    if dt.tzinfo is None:
        try:
            return dt.replace(tzinfo=ZoneInfo(tz))
        except Exception:
            return dt.replace(tzinfo=UTC)
    return dt


class DatetimeParser:
    def __init__(self):
        pass

    def parse(self, expression: str, tz: str = "Europe/Moscow", now: datetime | None = None) -> ParsedTime:
        if now is None:
            now = datetime.now(ZoneInfo(tz))
        else:
            now = _to_aware(now, tz)
        now = now.astimezone(ZoneInfo(tz))
        text = (expression or "").strip().lower()

        # duration-only
        dur = self.parse_duration(text)
        if dur is not None and not any(k in text for k in ["завтра", "сегодня", "в ", "вчера", "послезавтра", "через"]):
            # if expression is just duration, no date
            pass

        # special: до конца недели
        if "до конца недели" in text or "конец недели" in text:
            # sunday 23:59
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour < 23:
                days_until_sunday = 0
            target_date = (now + timedelta(days=days_until_sunday)).date()
            dt = datetime.combine(target_date, dtime(23, 59), tzinfo=ZoneInfo(tz))
            return ParsedTime(due_at=dt, starts_at=dt, date=dt, confidence=0.9)

        # next week
        if "на следующей неделе" in text or "следующая неделя" in text:
            # monday of next week
            monday = now.date() - timedelta(days=now.weekday())
            next_monday = monday + timedelta(days=7)
            dt = datetime.combine(next_monday, dtime(9, 0), tzinfo=ZoneInfo(tz))
            return ParsedTime(starts_at=dt, due_at=dt, date=dt, confidence=0.8, is_ambiguous=True)

        # day-of-week: в пятницу etc
        weekdays = {
            "понедельник": 0, "пн": 0,
            "вторник": 1, "вт": 1,
            "среда": 2, "среду": 2, "ср": 2,
            "четверг": 3, "чт": 3,
            "пятница": 4, "пятницу": 4, "пт": 4,
            "суббота": 5, "субботу": 5, "сб": 5,
            "воскресенье": 6, "вс": 6,
        }
        for word, wd in weekdays.items():
            if __import__("re").search(r"\b" + __import__("re").escape(word) + r"\b", text):
                # nearest future weekday
                delta = (wd - now.weekday()) % 7
                if delta == 0:
                    # today is that day -> next week? policy: if today friday and says friday, ambiguous
                    delta = 7
                target = now.date() + timedelta(days=delta)
                # extract time if present
                t = self._extract_time(text)
                if t is None:
                    t = dtime(9, 0)
                    ambiguous = True
                else:
                    ambiguous = False
                dt = datetime.combine(target, t, tzinfo=ZoneInfo(tz))
                return ParsedTime(starts_at=dt, due_at=dt, date=dt, time=t, is_ambiguous=ambiguous, confidence=0.85)

        # dateparser fallback
        settings = {
            "TIMEZONE": tz,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": now,
        }
        # handle "через N часов/минут"
        m = re.search(r"через\s+(\d+)\s*(час|часа|часов|минут|минуты|минуту|день|дня|дней)", text)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if "час" in unit:
                dt = now + timedelta(hours=n)
            elif "минут" in unit:
                dt = now + timedelta(minutes=n)
            elif "день" in unit or "дня" in unit or "дней" in unit:
                dt = now + timedelta(days=n)
            else:
                dt = now
            dt = dt.astimezone(ZoneInfo(tz))
            return ParsedTime(starts_at=dt, due_at=dt, date=dt, time=dt.timetz() if False else dt.timetz(), confidence=0.95)

        # default times of day
        tod_map = {"утром": dtime(9, 0), "днем": dtime(13, 0), "днём": dtime(13, 0), "вечером": dtime(18, 0), "ночью": dtime(22, 0)}
        for word, t in tod_map.items():
            if word in text:
                # need date; if none, ambiguous
                parsed_date = dateparser.parse(text, settings=settings)
                if parsed_date is None:
                    parsed_date = now
                parsed_date = _to_aware(parsed_date, tz).astimezone(ZoneInfo(tz))
                dt = datetime.combine(parsed_date.date(), t, tzinfo=ZoneInfo(tz))
                return ParsedTime(starts_at=dt, due_at=dt, date=dt, time=t, is_ambiguous=True, confidence=0.7)

        parsed = dateparser.parse(text, settings=settings)
        if parsed is not None:
            parsed = _to_aware(parsed, tz).astimezone(ZoneInfo(tz))
            extracted = self._extract_time(text)
            has_time = extracted is not None or bool(re.search(r"\d{1,2}[:.]\d{2}|\d{1,2}\s*(утра|вечера|дня|ночи|am|pm)", text))
            if extracted is not None:
                parsed = datetime.combine(parsed.date(), extracted, tzinfo=ZoneInfo(tz))
            ambig = not has_time
            pt = ParsedTime(starts_at=parsed, due_at=parsed, date=parsed, time=extracted if extracted is not None else parsed.timetz().replace(tzinfo=None), is_ambiguous=ambig, confidence=0.9 if has_time else 0.7)
            return pt

        # fallback: now
        return ParsedTime(starts_at=now, due_at=now, date=now, is_ambiguous=True, confidence=0.3)

    def parse_date(self, expression, tz="Europe/Moscow", now=None):
        return self.parse(expression, tz, now)

    def parse_datetime(self, expression, tz="Europe/Moscow", now=None):
        return self.parse(expression, tz, now)

    def parse_time(self, expression, tz="Europe/Moscow", now=None):
        r = self.parse(expression, tz, now)
        return r.time

    def _extract_time(self, text: str):
        import re
        m = re.search(r"(\d{1,2})[:.](\d{2})", text)
        if m:
            h = int(m.group(1)); mm = int(m.group(2))
            if 0 <= h <= 23 and 0 <= mm <= 59:
                from datetime import time as _t
                return _t(h, mm)
        m = re.search(r"в\s+(\d{1,2})\s*(утра|дня|вечера|ночи)?", text)
        if m:
            h = int(m.group(1))
            suffix = m.group(2)
            if suffix == "вечера" and h < 12:
                h += 12
            if suffix == "ночи" and h < 12:
                h += 12
            if 0 <= h <= 23:
                from datetime import time as _t
                return _t(h, 0)
        return None

    def parse_duration(self, expression: str) -> int | None:
        text = (expression or "").strip().lower()
        m = re.search(r"(\d+)\s*(час|часа|часов|минут|минуты|минута|день|дня|дней)", text)
        if not m:
            # word numbers
            word_nums = {"один":1,"одна":1,"два":2,"две":2,"три":3,"четыре":4,"пять":5,"пол":30,"полчаса":30}
            for w,n in word_nums.items():
                if w in text and ("час" in text or "минут" in text):
                    # handle below
                    pass
            return None
        n = int(m.group(1))
        unit = m.group(2)
        if "час" in unit:
            return n * 60
        if "минут" in unit:
            return n
        if "день" in unit or "дня" in unit or "дней" in unit:
            return n * 24 * 60
        return None


def parse_datetime(expression, tz="Europe/Moscow", now=None):
    return DatetimeParser().parse(expression, tz, now)

def parse_date(expression, tz="Europe/Moscow", now=None):
    return DatetimeParser().parse(expression, tz, now).date
