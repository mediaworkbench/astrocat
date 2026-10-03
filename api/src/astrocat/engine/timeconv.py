"""Conversions between local clock times and UTC moments."""

from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from astrocat.engine.profile import BirthData

NOON = time(12, 0)


def birth_moment(birth: BirthData) -> datetime:
    """UTC moment of birth. Unknown birth time falls back to local noon."""
    local_time = birth.time or NOON
    if birth.utc_offset_override is not None:
        tz = timezone(timedelta(hours=birth.utc_offset_override))
    else:
        tz = ZoneInfo(birth.timezone)
    return datetime.combine(birth.date, local_time, tzinfo=tz).astimezone(UTC)


def local_noon(day: date, tz_name: str) -> datetime:
    return datetime.combine(day, NOON, tzinfo=ZoneInfo(tz_name)).astimezone(UTC)


def local_day_bounds(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """UTC start and end of a local calendar day (23 or 25 hours on DST changes)."""
    tz = ZoneInfo(tz_name)
    start = datetime.combine(day, time(0, 0), tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=tz)
    return start.astimezone(UTC), end.astimezone(UTC)
