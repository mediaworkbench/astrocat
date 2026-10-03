"""Thin wrapper around libephemeris. The only module that talks to it."""

from dataclasses import dataclass
from datetime import UTC, datetime

import libephemeris as le

# Never download anything at runtime (concept §12): birth data stays local and
# the bundled data files cover our date range.
le.set_network_policy("sealed")

_BODY_IDS = {
    "sun": le.SUN,
    "moon": le.MOON,
    "mercury": le.MERCURY,
    "venus": le.VENUS,
    "mars": le.MARS,
    "jupiter": le.JUPITER,
    "saturn": le.SATURN,
    "uranus": le.URANUS,
    "neptune": le.NEPTUNE,
    "pluto": le.PLUTO,
}


@dataclass(frozen=True)
class Position:
    lon: float
    speed: float  # degrees per day; negative = retrograde


def julian_day(moment: datetime) -> float:
    """Julian Day (UT) for a timezone-aware datetime."""
    utc = moment.astimezone(UTC)
    hour = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3.6e9
    return le.julday(utc.year, utc.month, utc.day, hour)


def positions(moment: datetime, bodies: list[str]) -> dict[str, Position]:
    jd = julian_day(moment)
    result = {}
    for name in bodies:
        (lon, _lat, _dist, speed, _, _), _flag = le.calc_ut(jd, _BODY_IDS[name], le.FLG_SPEED)
        result[name] = Position(lon=lon, speed=speed)
    return result


def ascendant(moment: datetime, latitude: float, longitude: float) -> float:
    _cusps, angles = le.houses(julian_day(moment), latitude, longitude, ord("W"))
    return angles[0]
