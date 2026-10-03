from dataclasses import replace
from datetime import UTC, date, datetime, time

import libephemeris as le
import pytest

from astrocat.engine import ephemeris, zodiac
from astrocat.engine.daily import moon_exact_time
from astrocat.engine.profile import BirthData
from astrocat.engine.timeconv import birth_moment, local_day_bounds, local_noon

BERLIN = BirthData(
    date=date(1990, 7, 1),
    time=time(14, 0),
    place="Berlin",
    latitude=52.52,
    longitude=13.405,
    timezone="Europe/Berlin",
)


def test_reference_positions_j2000():
    # Published apparent geocentric longitudes for 2000-01-01 12:00.
    pos = ephemeris.positions(datetime(2000, 1, 1, 12, tzinfo=UTC), ["sun", "moon"])
    assert pos["sun"].lon == pytest.approx(280.37, abs=0.05)
    assert pos["moon"].lon == pytest.approx(223.32, abs=0.05)


def test_runtime_downloads_are_disabled():
    assert le.get_network_policy() == "sealed"


def test_birth_moment_summer_and_winter_time():
    assert birth_moment(BERLIN) == datetime(1990, 7, 1, 12, 0, tzinfo=UTC)  # CEST, UTC+2
    winter = replace(BERLIN, date=date(1990, 1, 15))
    assert birth_moment(winter) == datetime(1990, 1, 15, 13, 0, tzinfo=UTC)  # CET, UTC+1


def test_birth_moment_offset_override():
    override = replace(BERLIN, utc_offset_override=5.5)
    assert birth_moment(override) == datetime(1990, 7, 1, 8, 30, tzinfo=UTC)


def test_unknown_birth_time_uses_local_noon():
    unknown = replace(BERLIN, time=None)
    assert birth_moment(unknown) == datetime(1990, 7, 1, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize(("day", "hours"), [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25), (date(2026, 10, 3), 24)])
def test_local_day_length_across_dst(day, hours):
    start, end = local_day_bounds(day, "Europe/Berlin")
    assert (end - start).total_seconds() == hours * 3600


def test_local_noon():
    assert local_noon(date(2026, 10, 3), "Europe/Berlin") == datetime(2026, 10, 3, 10, 0, tzinfo=UTC)


def test_moon_exact_time_matches_ephemeris():
    start, end = local_day_bounds(date(2026, 10, 3), "Europe/Berlin")
    lon_start = ephemeris.positions(start, ["moon"])["moon"].lon
    lon_end = ephemeris.positions(end, ["moon"])["moon"].lon
    target = zodiac.norm(lon_start + 5.0)  # a point the Moon passes during the day

    exact = moon_exact_time(lon_start, lon_end, start, end, target, 0)
    assert exact is not None and start < exact < end
    actual = ephemeris.positions(exact, ["moon"])["moon"].lon
    assert zodiac.separation(actual, target) < 0.05

    behind = zodiac.norm(lon_start - 5.0)  # already passed before the day started
    assert moon_exact_time(lon_start, lon_end, start, end, behind, 0) is None
