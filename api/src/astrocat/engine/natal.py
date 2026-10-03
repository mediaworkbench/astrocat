"""Natal (birth) chart."""

from typing import Any

from astrocat.engine import ephemeris, zodiac
from astrocat.engine.config import settings
from astrocat.engine.profile import Profile
from astrocat.engine.timeconv import birth_moment


def compute_natal(profile: Profile) -> dict[str, Any]:
    """Positions, signs and Whole Sign houses of the birth chart.

    With an unknown birth time there is no Ascendant, and houses are solar
    houses: Whole Sign counted from the Sun's sign.
    """
    birth = profile.birth
    moment = birth_moment(birth)
    positions = ephemeris.positions(moment, settings()["bodies"])

    if birth.time_known:
        asc_lon = ephemeris.ascendant(moment, birth.latitude, birth.longitude)
        first_house = zodiac.sign_index(asc_lon)
        ascendant = {"lon": round(asc_lon, 4), "sign": zodiac.sign_of(asc_lon)}
    else:
        first_house = zodiac.sign_index(positions["sun"].lon)
        ascendant = None

    bodies = {
        name: {
            "lon": round(pos.lon, 4),
            "sign": zodiac.sign_of(pos.lon),
            "degree": round(zodiac.degree_in_sign(pos.lon), 2),
            "house": zodiac.whole_sign_house(pos.lon, first_house),
            "retrograde": pos.speed < 0,
        }
        for name, pos in positions.items()
    }
    return {
        "birth_time_known": birth.time_known,
        "moment_utc": moment.isoformat(),
        "houses": "whole_sign" if birth.time_known else "solar",
        "first_house_sign": zodiac.SIGNS[first_house],
        "ascendant": ascendant,
        "bodies": bodies,
    }


def natal_points(natal: dict[str, Any]) -> dict[str, float]:
    """Longitudes that transits can aspect: all bodies, plus the Ascendant if known."""
    points = {name: body["lon"] for name, body in natal["bodies"].items()}
    if natal["ascendant"]:
        points["ascendant"] = natal["ascendant"]["lon"]
    return points
