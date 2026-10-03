"""Pure zodiac math: signs, houses, angular separation, Moon phases."""

SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)  # fmt: skip

MOON_PHASES = (
    "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
    "full_moon", "waning_gibbous", "last_quarter", "waning_crescent",
)  # fmt: skip


def norm(lon: float) -> float:
    return lon % 360.0


def sign_index(lon: float) -> int:
    return int(norm(lon) // 30)


def sign_of(lon: float) -> str:
    return SIGNS[sign_index(lon)]


def degree_in_sign(lon: float) -> float:
    return norm(lon) % 30.0


def separation(a: float, b: float) -> float:
    """Shortest angular distance between two longitudes, 0-180."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def whole_sign_house(lon: float, first_house_sign: int) -> int:
    """House 1-12 in the Whole Sign system, house 1 being `first_house_sign`."""
    return (sign_index(lon) - first_house_sign) % 12 + 1


def moon_phase(sun_lon: float, moon_lon: float) -> str:
    """One of 8 phases, each centered on its exact elongation (0, 45, 90, ...)."""
    elongation = norm(moon_lon - sun_lon)
    return MOON_PHASES[int(norm(elongation + 22.5) // 45)]


def aspect_points(natal_lon: float, angle: float) -> list[float]:
    """Longitudes where a transiting body forms `angle` to `natal_lon`."""
    points = {round(norm(natal_lon + angle), 9), round(norm(natal_lon - angle), 9)}
    return sorted(points)
