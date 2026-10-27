from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.datetime_parser import DatetimeParser

TZ = "Europe/Moscow"
NOW = datetime(2026, 10, 22, 12, 0, tzinfo=ZoneInfo(TZ))  # Thursday


@pytest.fixture
def parser() -> DatetimeParser:
    return DatetimeParser()


def test_tomorrow_with_explicit_time(parser):
    parsed = parser.parse("завтра в 10 утра", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 23, 10, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.due_at == parsed.starts_at
    assert parsed.is_ambiguous is False


def test_tomorrow_at_one_oclock(parser):
    parsed = parser.parse("завтра в час", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 23, 13, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.due_at == parsed.starts_at
    assert parsed.duration_minutes is None
    assert parsed.is_ambiguous is False


def test_one_oclock_with_part_of_day(parser):
    day = parser.parse("завтра в час дня", TZ, NOW)
    assert day.starts_at == datetime(2026, 10, 23, 13, 0, tzinfo=ZoneInfo(TZ))

    night = parser.parse("в час ночи", TZ, NOW)
    assert night.time.isoformat() == "01:00:00"


def test_word_number_hours(parser):
    parsed = parser.parse("завтра в два часа", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 23, 2, 0, tzinfo=ZoneInfo(TZ))


def test_today_and_tomorrow_are_day_ranges(parser):
    today = parser.parse("сегодня", TZ, NOW)
    assert today.starts_at == datetime(2026, 10, 22, 0, 0, tzinfo=ZoneInfo(TZ))
    assert today.ends_at == datetime(2026, 10, 22, 23, 59, 59, 999999, tzinfo=ZoneInfo(TZ))
    assert today.due_at == today.ends_at
    assert today.is_ambiguous is True

    tomorrow = parser.parse("завтра", TZ, NOW)
    assert tomorrow.starts_at == datetime(2026, 10, 23, 0, 0, tzinfo=ZoneInfo(TZ))
    assert tomorrow.ends_at == datetime(2026, 10, 23, 23, 59, 59, 999999, tzinfo=ZoneInfo(TZ))


def test_next_week_is_a_range(parser):
    parsed = parser.parse("на следующей неделе", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 26, 0, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.ends_at == datetime(2026, 11, 1, 23, 59, 59, 999999, tzinfo=ZoneInfo(TZ))
    assert parsed.is_ambiguous is True


def test_end_of_week_is_a_deadline(parser):
    parsed = parser.parse("до конца недели", TZ, NOW)
    assert parsed.starts_at is None
    assert parsed.due_at == datetime(2026, 10, 25, 23, 59, 59, 999999, tzinfo=ZoneInfo(TZ))
    assert parsed.is_ambiguous is False


def test_duration_expressions(parser):
    assert parser.parse_duration("на час") == 60
    assert parser.parse_duration("полчаса") == 30
    assert parser.parse_duration("1,5 часа") == 90
    assert parser.parse_duration("2 часа 30 минут") == 150
    assert parser.parse_duration("два часа") == 120


def test_duration_without_start_time_is_ambiguous(parser):
    parsed = parser.parse("на час", TZ, NOW)
    assert parsed.duration_minutes == 60
    assert parsed.starts_at is None
    assert parsed.is_ambiguous is True


def test_date_with_duration_but_without_time(parser):
    parsed = parser.parse("завтра на час", TZ, NOW)
    assert parsed.duration_minutes == 60
    assert parsed.date == datetime(2026, 10, 23, 0, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.starts_at is None
    assert parsed.is_ambiguous is True


def test_time_only_is_ambiguous(parser):
    parsed = parser.parse("в 10 утра", TZ, NOW)
    assert parsed.time.isoformat() == "10:00:00"
    assert parsed.starts_at is None
    assert parsed.is_ambiguous is True

    minutes = parser.parse("в 10 часов 30 минут", TZ, NOW)
    assert minutes.time.isoformat() == "10:30:00"
    assert minutes.starts_at is None


def test_weekday(parser):
    friday = parser.parse("в пятницу", TZ, NOW)
    assert friday.starts_at == datetime(2026, 10, 23, 9, 0, tzinfo=ZoneInfo(TZ))
    assert friday.is_ambiguous is True

    friday_with_time = parser.parse("в пятницу в 15:00", TZ, NOW)
    assert friday_with_time.starts_at == datetime(2026, 10, 23, 15, 0, tzinfo=ZoneInfo(TZ))
    assert friday_with_time.is_ambiguous is False


def test_weekday_today_is_ambiguous(parser):
    friday_now = datetime(2026, 10, 23, 8, 0, tzinfo=ZoneInfo(TZ))
    parsed = parser.parse("в пятницу", TZ, friday_now)
    assert parsed.starts_at == datetime(2026, 10, 23, 9, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.is_ambiguous is True


def test_relative_point(parser):
    parsed = parser.parse("через два часа", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 22, 14, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.is_ambiguous is False


def test_explicit_iso_datetime(parser):
    parsed = parser.parse("2026-10-23T10:00:00+03:00", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 23, 10, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.is_ambiguous is False


def test_unknown_expression_does_not_invent_a_date(parser):
    parsed = parser.parse("ерунда какая-то", TZ, NOW)
    assert parsed.starts_at is None
    assert parsed.due_at is None
    assert parsed.date is None
    assert parsed.is_ambiguous is True
    assert parsed.confidence == 0.0


def test_english_tomorrow_from_llm_arguments(parser):
    # Providers sometimes normalize «завтра» to «tomorrow» inside tool args.
    parsed = parser.parse("tomorrow в 16:00", TZ, NOW)
    assert parsed.starts_at == datetime(2026, 10, 23, 16, 0, tzinfo=ZoneInfo(TZ))
    assert parsed.is_ambiguous is False


def test_english_weekday_and_relative_duration(parser):
    parsed = parser.parse("friday", TZ, NOW)
    assert parsed.starts_at.date().isoformat() == "2026-10-23"

    relative = parser.parse("in 2 hours", TZ, NOW)
    assert relative.starts_at == datetime(2026, 10, 22, 14, 0, tzinfo=ZoneInfo(TZ))


def test_invalid_timezone(parser):
    with pytest.raises(ValueError, match="invalid_timezone"):
        parser.parse("завтра", "No/Such_Zone", NOW)


def test_range_with_month_at_the_end(parser):
    assert parser.parse_range("с 3 по 7 ноября", TZ, NOW) == (
        date(2026, 11, 3),
        date(2026, 11, 7),
    )


def test_range_with_month_on_both_sides(parser):
    assert parser.parse_range("с 28 октября по 3 ноября", TZ, NOW) == (
        date(2026, 10, 28),
        date(2026, 11, 3),
    )


def test_range_with_dash(parser):
    assert parser.parse_range("3–7 ноября", TZ, NOW) == (
        date(2026, 11, 3),
        date(2026, 11, 7),
    )


def test_range_keeps_recent_past_in_current_year(parser):
    # NOW is 22 October: listing a recent past range should not jump a year.
    assert parser.parse_range("с 1 по 5 октября", TZ, NOW) == (
        date(2026, 10, 1),
        date(2026, 10, 5),
    )


def test_range_far_in_the_past_means_next_year(parser):
    assert parser.parse_range("с 3 по 7 января", TZ, NOW) == (
        date(2027, 1, 3),
        date(2027, 1, 7),
    )


def test_range_with_explicit_year(parser):
    assert parser.parse_range("с 3 по 7 ноября 2027", TZ, NOW) == (
        date(2027, 11, 3),
        date(2027, 11, 7),
    )


def test_range_rejects_unknown_text(parser):
    assert parser.parse_range("ерунда какая-то", TZ, NOW) is None
