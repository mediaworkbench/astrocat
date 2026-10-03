"""User birth profile, loaded from YAML (M1) and later from the database."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from astrocat.engine.config import engine_version

LANGUAGES = ("en", "es", "de")


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class BirthData:
    date: date
    time: time | None  # None = unknown, noon fallback
    place: str
    latitude: float
    longitude: float
    timezone: str  # IANA zone of the birth place
    utc_offset_override: float | None = None  # hours, overrides `timezone`

    @property
    def time_known(self) -> bool:
        return self.time is not None


@dataclass(frozen=True)
class Profile:
    display_name: str
    language: str
    current_timezone: str
    birth: BirthData

    def input_hash(self) -> str:
        """Hash of everything that determines the engine output (concept §8)."""
        data = {
            "birth": asdict(self.birth),
            "current_timezone": self.current_timezone,
            "engine_version": engine_version(),
        }
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _parse_time(value: object) -> time | None:
    if value is None:
        return None
    if isinstance(value, int):
        # YAML 1.1 reads an unquoted 14:35 as a base-60 integer.
        raise ProfileError('birth time must be quoted, e.g. time: "14:35"')
    try:
        return time.fromisoformat(str(value))
    except ValueError as exc:
        raise ProfileError(f"invalid birth time: {value!r}") from exc


def _check_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except Exception as exc:
        raise ProfileError(f"unknown timezone: {name!r}") from exc
    return name


def profile_from_dict(data: dict) -> Profile:
    try:
        birth = data["birth"]
        birth_date = birth["date"]
        if not isinstance(birth_date, date):
            birth_date = date.fromisoformat(str(birth_date))
        latitude = float(birth["latitude"])
        longitude = float(birth["longitude"])
        override = birth.get("utc_offset_override")
        profile = Profile(
            display_name=str(data["display_name"]),
            language=str(data.get("language", "en")),
            current_timezone=_check_timezone(data["current_timezone"]),
            birth=BirthData(
                date=birth_date,
                time=_parse_time(birth.get("time")),
                place=str(birth.get("place", "")),
                latitude=latitude,
                longitude=longitude,
                timezone=_check_timezone(birth["timezone"]),
                utc_offset_override=None if override is None else float(override),
            ),
        )
    except KeyError as exc:
        raise ProfileError(f"missing field: {exc.args[0]}") from exc
    if profile.language not in LANGUAGES:
        raise ProfileError(f"language must be one of {LANGUAGES}")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ProfileError("latitude/longitude out of range")
    return profile


def load_profile(path: str | Path) -> Profile:
    with open(path, encoding="utf-8") as f:
        return profile_from_dict(yaml.safe_load(f))
