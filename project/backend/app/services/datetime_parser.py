from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from datetime import time as dtime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


_WEEKDAYS = {
    "понедельник": 0,
    "понедельника": 0,
    "пн": 0,
    "вторник": 1,
    "вторника": 1,
    "вт": 1,
    "среда": 2,
    "среду": 2,
    "среды": 2,
    "ср": 2,
    "четверг": 3,
    "четверга": 3,
    "чт": 3,
    "пятница": 4,
    "пятницу": 4,
    "пятницы": 4,
    "пт": 4,
    "суббота": 5,
    "субботу": 5,
    "субботы": 5,
    "сб": 5,
    "воскресенье": 6,
    "воскресенья": 6,
    "вс": 6,
}

_MONTHS = {
    "января": 1,
    "январь": 1,
    "январе": 1,
    "февраля": 2,
    "февраль": 2,
    "феврале": 2,
    "марта": 3,
    "март": 3,
    "марте": 3,
    "апреля": 4,
    "апрель": 4,
    "апреле": 4,
    "мая": 5,
    "май": 5,
    "мае": 5,
    "июня": 6,
    "июнь": 6,
    "июне": 6,
    "июля": 7,
    "июль": 7,
    "июле": 7,
    "августа": 8,
    "август": 8,
    "августе": 8,
    "сентября": 9,
    "сентябрь": 9,
    "сентябре": 9,
    "октября": 10,
    "октябрь": 10,
    "октябре": 10,
    "ноября": 11,
    "ноябрь": 11,
    "ноябре": 11,
    "декабря": 12,
    "декабрь": 12,
    "декабре": 12,
}

_WORD_NUMBERS = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "одну": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "девяносто": 90,
    "сто": 100,
}

_TOD = {
    "утром": dtime(9, 0),
    "утро": dtime(9, 0),
    "днем": dtime(13, 0),
    "день": dtime(13, 0),
    "вечером": dtime(18, 0),
    "вечер": dtime(18, 0),
    "ночью": dtime(22, 0),
    "ночь": dtime(22, 0),
}

_DURATION_MARKERS = re.compile(r"\b(на|через|в течение|длительностью|продолжительностью)\b")


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().replace("ё", "е").strip().split())


_FOREIGN_DATES = (
    (re.compile(r"\bday after tomorrow\b"), "послезавтра"),
    (re.compile(r"\btomorrow\b"), "завтра"),
    (re.compile(r"\btoday\b"), "сегодня"),
    (re.compile(r"\byesterday\b"), "вчера"),
    (re.compile(r"\bnext week\b"), "на следующей неделе"),
    (re.compile(r"\bthis week\b"), "на этой неделе"),
)

_FOREIGN_WEEKDAYS = {
    "monday": "понедельник",
    "tuesday": "вторник",
    "wednesday": "среду",
    "thursday": "четверг",
    "friday": "пятницу",
    "saturday": "субботу",
    "sunday": "воскресенье",
}

_FOREIGN_NUMBERS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
}

_FOREIGN_UNITS = {
    "minute": "минуту",
    "minutes": "минут",
    "hour": "час",
    "hours": "часа",
    "day": "день",
    "days": "дня",
    "week": "неделю",
    "weeks": "недели",
}

_FOREIGN_RELATIVE = re.compile(
    r"\bin\s+(\d+|"
    + "|".join(_FOREIGN_NUMBERS)
    + r")\s+(minutes?|hours?|days?|weeks?)\b"
)


def _translate_foreign_dates(text: str) -> str:
    """Translate English relative dates the LLM may put into tool arguments.

    The model is asked to keep time_expression in Russian, but a provider can
    still normalize «завтра» to «tomorrow». Treating those tokens as Russian
    keeps the clarification flow working instead of asking the same question
    forever.
    """
    lowered = (text or "").lower()
    for pattern, replacement in _FOREIGN_DATES:
        lowered = pattern.sub(replacement, lowered)
    for name, russian in _FOREIGN_WEEKDAYS.items():
        lowered = re.sub(rf"\b{name}\b", russian, lowered)

    def _relative(match: re.Match[str]) -> str:
        amount = _FOREIGN_NUMBERS.get(match.group(1), match.group(1))
        return f"через {amount} {_FOREIGN_UNITS[match.group(2)]}"

    return _FOREIGN_RELATIVE.sub(_relative, lowered)


def _tz(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("invalid_timezone") from exc


def _to_aware(value: datetime, timezone: str) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=_tz(timezone))
    return value.astimezone(_tz(timezone))


def _day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    zone = _tz(timezone)
    start = datetime.combine(day, dtime(0, 0), tzinfo=zone)
    end = datetime.combine(day, dtime(23, 59, 59, 999999), tzinfo=zone)
    return start, end


def _week_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    monday = day - timedelta(days=day.weekday())
    start, _ = _day_bounds(monday, timezone)
    end, _ = _day_bounds(monday + timedelta(days=6), timezone)
    start = datetime.combine(monday, dtime(0, 0), tzinfo=_tz(timezone))
    end = datetime.combine(monday + timedelta(days=6), dtime(23, 59, 59, 999999), tzinfo=_tz(timezone))
    return start, end


def _replace_word_numbers(text: str) -> str:
    for word, number in sorted(_WORD_NUMBERS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(word)}\b", str(number), text)
    return text


def _parse_duration(text: str) -> int | None:
    text = _normalize(text)
    if "полчаса" in text or "пол часа" in text:
        return 30
    if "полтора часа" in text or "полторы часа" in text:
        return 90

    text = _replace_word_numbers(text)
    pattern = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(час(?:а|ов)?|мин(?:ут(?:а|ы)?)?|день|дня|дней|недел(?:ю|и|ь)?)\b"
    )
    total = 0
    found = False
    for match in pattern.finditer(text):
        raw, unit = match.group(1).replace(",", "."), match.group(2)
        amount = float(raw)
        if unit.startswith("час"):
            total += round(amount * 60)
        elif unit.startswith("мин"):
            total += round(amount)
        elif unit in {"день", "дня", "дней"}:
            total += round(amount * 24 * 60)
        elif unit.startswith("недел"):
            total += round(amount * 7 * 24 * 60)
        else:
            continue
        found = True

    if found:
        return total or None

    # «на час», «час», «минуту» без числа.
    if re.search(r"\bчас\b", text):
        return 60
    if re.search(r"\bминута\b|\bминуту\b", text):
        return 1
    return None


def _is_time_phrase(text: str) -> bool:
    text = _replace_word_numbers(_normalize(text))
    return bool(
        re.search(
            r"\bв\s+(?:\d{1,2}|час)(\s*час(?:а|ов)?)?"
            r"(\s+\d{1,2}\s*минут(?:ы)?)?\b",
            text,
        )
        or re.search(r"\b\d{1,2}[:.]\d{2}\b", text)
    )


def _parse_time(text: str) -> dtime | None:
    text = _replace_word_numbers(_normalize(text))
    if "полдень" in text:
        return dtime(12, 0)
    if "полночь" in text:
        return dtime(0, 0)

    # «в час», «в час дня», «в час ночи» — час без числа.
    match = re.search(r"\bв\s+час\b(?:\s+(утра|дня|вечера|ночи))?", text)
    if match:
        suffix = match.group(1)
        if suffix in {"утра", "ночи"}:
            return dtime(1, 0)
        return dtime(13, 0)

    # 10:30 / 10.30 (но не 23.10.2026)
    match = re.search(r"(?<!\d)(\d{1,2})[:.](\d{2})(?!\d)(?!\.\d)", text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return dtime(hour, minute)

    # в 10, в 10 утра, в 10 часов, в 10 часов 30 минут
    match = re.search(
        r"\bв\s+(\d{1,2})(?:\s*час(?:а|ов)?)?(?:\s+(\d{1,2})\s*минут(?:ы)?)?\s*(утра|дня|вечера|ночи)?\b",
        text,
    )
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        suffix = match.group(3)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        if suffix in {"дня"} and hour < 12:
            hour += 12
        elif suffix in {"вечера", "ночи"}:
            if hour == 12:
                hour = 0
            elif hour < 12:
                hour += 12
        # «в 3 ночи» → 03:00, «в 12 ночи» → 00:00
        return dtime(hour, minute)

    # 10 утра (без «в»)
    match = re.search(r"\b(\d{1,2})\s*(утра|дня|вечера|ночи)\b", text)
    if match:
        hour = int(match.group(1))
        suffix = match.group(2)
        if suffix == "дня" and hour < 12:
            hour += 12
        elif suffix in {"вечера", "ночи"}:
            if hour == 12:
                hour = 0
            elif hour < 12:
                hour += 12
        if 0 <= hour <= 23:
            return dtime(hour, 0)
    return None


def _parse_tod(text: str) -> dtime | None:
    for word, value in _TOD.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return value
    return None


def _parse_explicit_date(text: str, now: datetime) -> date | None:
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b", text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None

    match = re.search(r"\b(\d{1,2})\s+([а-я]+)\b", text)
    if match:
        day = int(match.group(1))
        month_number = _MONTHS.get(match.group(2))
        if month_number:
            year = now.year
            try:
                result = date(year, month_number, day)
            except ValueError:
                return None
            if result < now.date():
                try:
                    result = date(year + 1, month_number, day)
                except ValueError:
                    return None
            return result
    return None


_RANGE_WITH_PREPOSITION = re.compile(
    r"\b(?:с|со)\s+(\d{1,2})(?:\s+([а-я]+))?(?:\s+(\d{4}))?"
    r"\s*(?:по|до)\s*(\d{1,2})(?:\s+([а-я]+))?(?:\s+(\d{4}))?"
)

_RANGE_WITH_DASH = re.compile(
    r"\b(\d{1,2})\s*(?:-|–|—)\s*(\d{1,2})\s+([а-я]+)(?:\s+(\d{4}))?"
)


def _range_dates(text: str, now: datetime) -> tuple[date, date] | None:
    """Parse a closed date range: «с 3 по 7 ноября», «3–7 ноября»."""
    start_day: int | None = None
    end_day: int | None = None
    start_month: int | None = None
    end_month: int | None = None
    year: int | None = None
    explicit_year = False

    match = _RANGE_WITH_PREPOSITION.search(text)
    if match:
        start_day = int(match.group(1))
        start_month = _MONTHS.get(match.group(2) or "")
        end_day = int(match.group(4))
        end_month = _MONTHS.get(match.group(5) or "")
        raw_year = match.group(3) or match.group(6)
        if raw_year:
            year = int(raw_year)
            explicit_year = True
    else:
        match = _RANGE_WITH_DASH.search(text)
        if not match:
            return None
        start_day = int(match.group(1))
        end_day = int(match.group(2))
        end_month = _MONTHS.get(match.group(3))
        if match.group(4):
            year = int(match.group(4))
            explicit_year = True

    # «с 3 по 7 ноября» — месяц указан один раз в конце.
    if start_month is None:
        start_month = end_month
    if end_month is None:
        end_month = start_month
    if start_day is None or end_day is None or not start_month or not end_month:
        return None

    if year is None:
        year = now.year
    try:
        start = date(year, start_month, start_day)
        end_year = year + (1 if end_month < start_month else 0)
        end = date(end_year, end_month, end_day)
    except ValueError:
        return None
    if end < start:
        return None

    # Без года далёкое прошлое считаем ближайшим будущим: «с 3 по 7 января»
    # в октябре — это январь следующего года, а «с 1 по 5 октября» остаётся
    # текущим годом, чтобы можно было смотреть недавнюю историю.
    if not explicit_year and end < now.date() - timedelta(days=60):
        try:
            start = start.replace(year=start.year + 1)
            end = end.replace(year=end.year + 1)
        except ValueError:
            return None
    return start, end


def _parse_date_keyword(text: str, now: datetime) -> tuple[date, bool] | None:
    if re.search(r"\bпослезавтра\b", text):
        return now.date() + timedelta(days=2), False
    if re.search(r"\bзавтра\b", text):
        return now.date() + timedelta(days=1), False
    if re.search(r"\bсегодня\b", text):
        return now.date(), False
    if re.search(r"\bвчера\b", text):
        return now.date() - timedelta(days=1), False

    for word, weekday in _WEEKDAYS.items():
        if not re.search(rf"\b{re.escape(word)}\b", text):
            continue
        if "следующ" in text:
            monday = now.date() - timedelta(days=now.weekday())
            return monday + timedelta(days=7 + weekday), False
        delta = (weekday - now.weekday()) % 7
        ambiguous = delta == 0
        return now.date() + timedelta(days=delta), ambiguous
    return None


def _parse_week_or_deadline(text: str, now: datetime, timezone: str) -> ParsedTime | None:
    if "до конца недели" in text or "к концу недели" in text or "конец недели" in text:
        _, end = _week_bounds(now.date(), timezone)
        return ParsedTime(
            due_at=end,
            date=end,
            is_ambiguous=False,
            confidence=0.9,
        )

    if "до конца дня" in text or "к концу дня" in text:
        _, end = _day_bounds(now.date(), timezone)
        return ParsedTime(
            due_at=end,
            date=end,
            is_ambiguous=False,
            confidence=0.9,
        )

    if "на следующей неделе" in text or "следующая неделя" in text or "следующей неделе" in text:
        next_monday = now.date() - timedelta(days=now.weekday()) + timedelta(days=7)
        start, end = _week_bounds(next_monday, timezone)
        return ParsedTime(
            starts_at=start,
            ends_at=end,
            due_at=end,
            date=start,
            is_ambiguous=True,
            confidence=0.8,
        )

    if "на этой неделе" in text or "текущая неделя" in text or "текущей неделе" in text:
        start, end = _week_bounds(now.date(), timezone)
        return ParsedTime(
            starts_at=start,
            ends_at=end,
            due_at=end,
            date=start,
            is_ambiguous=True,
            confidence=0.8,
        )
    return None


def _parse_relative(text: str, now: datetime, timezone: str) -> ParsedTime | None:
    if "через" not in text:
        return None
    tail = text.split("через", 1)[1].strip()
    minutes = _parse_duration(tail)
    if not minutes:
        return None
    point = (now + timedelta(minutes=minutes)).astimezone(_tz(timezone))
    return ParsedTime(
        starts_at=point,
        due_at=point,
        date=point,
        time=point.time(),
        is_ambiguous=False,
        confidence=0.95,
    )


class DatetimeParser:
    def parse(self, expression: str, tz: str = "Europe/Moscow", now: datetime | None = None) -> ParsedTime:
        zone = _tz(tz)
        if now is None:
            now = datetime.now(zone)
        else:
            now = _to_aware(now, tz)
        now = now.astimezone(zone)
        text = _normalize(_translate_foreign_dates(expression))

        if not text:
            return ParsedTime(is_ambiguous=True, confidence=0.0)

        # Явный ISO-формат: 2026-10-23T10:00:00+03:00
        iso_match = re.search(
            r"\b(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:?\d{2}|Z)?)\b",
            expression,
            flags=re.IGNORECASE,
        )
        if iso_match:
            raw = iso_match.group(1).replace(" ", "T").replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                parsed = None
            if parsed is not None:
                parsed = _to_aware(parsed, tz)
                return ParsedTime(
                    starts_at=parsed,
                    due_at=parsed,
                    date=parsed,
                    time=parsed.time(),
                    is_ambiguous=False,
                    confidence=1.0,
                )

        week_or_deadline = _parse_week_or_deadline(text, now, tz)
        if week_or_deadline is not None:
            return week_or_deadline

        relative = _parse_relative(text, now, tz)
        if relative is not None:
            return relative

        date_info = _parse_date_keyword(text, now)
        date_ambiguous = False
        target_date: date | None = None
        if date_info is not None:
            target_date, date_ambiguous = date_info
        else:
            target_date = _parse_explicit_date(text, now)

        time_value = _parse_time(text)
        tod_value = _parse_tod(text)

        duration = _parse_duration(text)
        if time_value is not None and _is_time_phrase(text) and not _DURATION_MARKERS.search(text):
            duration = None

        if target_date is not None and time_value is not None:
            start = datetime.combine(target_date, time_value, tzinfo=zone)
            ends = start + timedelta(minutes=duration) if duration else None
            return ParsedTime(
                starts_at=start,
                ends_at=ends,
                due_at=start,
                duration_minutes=duration,
                date=start,
                time=time_value,
                is_ambiguous=date_ambiguous,
                confidence=0.95,
            )

        if target_date is not None and tod_value is not None:
            start = datetime.combine(target_date, tod_value, tzinfo=zone)
            ends = start + timedelta(minutes=duration) if duration else None
            return ParsedTime(
                starts_at=start,
                ends_at=ends,
                due_at=start,
                duration_minutes=duration,
                date=start,
                time=tod_value,
                is_ambiguous=True,
                confidence=0.7,
            )

        if target_date is not None:
            # «завтра на час»: дата есть, но время начала не задано.
            if duration is not None:
                return ParsedTime(
                    duration_minutes=duration,
                    date=datetime.combine(target_date, dtime(0, 0), tzinfo=zone),
                    is_ambiguous=True,
                    confidence=0.6,
                )
            # «сегодня»/«завтра» без времени — диапазон дня.
            if re.search(r"\b(сегодня|завтра|послезавтра|вчера)\b", text):
                start, end = _day_bounds(target_date, tz)
                return ParsedTime(
                    starts_at=start,
                    ends_at=end,
                    due_at=end,
                    date=start,
                    is_ambiguous=True,
                    confidence=0.75,
                )
            start = datetime.combine(target_date, dtime(9, 0), tzinfo=zone)
            ends = start + timedelta(minutes=duration) if duration else None
            return ParsedTime(
                starts_at=start,
                ends_at=ends,
                due_at=start,
                duration_minutes=duration,
                date=start,
                time=dtime(9, 0),
                is_ambiguous=True,
                confidence=0.75,
            )

        if time_value is not None:
            return ParsedTime(
                duration_minutes=duration,
                time=time_value,
                is_ambiguous=True,
                confidence=0.6,
            )

        if tod_value is not None:
            start = datetime.combine(now.date(), tod_value, tzinfo=zone)
            ends = start + timedelta(minutes=duration) if duration else None
            return ParsedTime(
                starts_at=start,
                ends_at=ends,
                due_at=start,
                duration_minutes=duration,
                date=start,
                time=tod_value,
                is_ambiguous=True,
                confidence=0.7,
            )

        if duration is not None:
            return ParsedTime(duration_minutes=duration, is_ambiguous=True, confidence=0.5)

        # Осторожный fallback: только если dateparser действительно распознал дату.
        settings = {
            "TIMEZONE": tz,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": now,
        }
        parsed = dateparser.parse(text, languages=["ru"], settings=settings)
        if parsed is not None:
            parsed = _to_aware(parsed, tz).astimezone(zone)
            if time_value is None:
                start = datetime.combine(parsed.date(), dtime(9, 0), tzinfo=zone)
                return ParsedTime(
                    starts_at=start,
                    due_at=start,
                    date=start,
                    time=dtime(9, 0),
                    is_ambiguous=True,
                    confidence=0.5,
                )
            start = datetime.combine(parsed.date(), time_value, tzinfo=zone)
            return ParsedTime(
                starts_at=start,
                due_at=start,
                date=start,
                time=time_value,
                is_ambiguous=False,
                confidence=0.7,
            )

        # Не додумываем дату: пусть вызывающий код задаст уточнение.
        return ParsedTime(is_ambiguous=True, confidence=0.0)

    def parse_date(self, expression, tz="Europe/Moscow", now=None):
        return self.parse(expression, tz, now).date

    def parse_range(
        self,
        expression: str,
        tz: str = "Europe/Moscow",
        now: datetime | None = None,
    ) -> tuple[date, date] | None:
        """Return inclusive (start, end) dates for a range expression."""
        zone = _tz(tz)
        if now is None:
            now = datetime.now(zone)
        else:
            now = _to_aware(now, tz).astimezone(zone)
        text = _normalize(_translate_foreign_dates(expression))
        if not text:
            return None
        return _range_dates(text, now)

    def parse_datetime(self, expression, tz="Europe/Moscow", now=None):
        return self.parse(expression, tz, now)

    def parse_time(self, expression, tz="Europe/Moscow", now=None):
        return self.parse(expression, tz, now).time

    def parse_duration(self, expression: str) -> int | None:
        return _parse_duration(expression)


def parse_datetime(expression, tz="Europe/Moscow", now=None):
    return DatetimeParser().parse(expression, tz, now)


def parse_date(expression, tz="Europe/Moscow", now=None):
    return DatetimeParser().parse(expression, tz, now).date


def parse_range(expression, tz="Europe/Moscow", now=None):
    return DatetimeParser().parse_range(expression, tz, now)
