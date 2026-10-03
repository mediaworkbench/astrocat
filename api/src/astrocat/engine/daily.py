"""Daily computation: transits → factors → category scores → selection (concept §5.3)."""

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from astrocat.engine import ephemeris, zodiac
from astrocat.engine.config import engine_version, keywords, settings
from astrocat.engine.natal import compute_natal, natal_points
from astrocat.engine.profile import Profile
from astrocat.engine.timeconv import local_day_bounds, local_noon

CATEGORIES = ("love", "work", "energy", "mood")


@dataclass
class Factor:
    kind: str  # "aspect" or "placement"
    transit: str
    house: int  # natal house the transiting body is in
    weight: float
    value: float  # -1 (tense) .. +1 (harmonious)
    aspect: str | None = None
    natal: str | None = None
    orb: float | None = None
    exact_at: datetime | None = None  # Moon aspects only
    background: bool = False
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    id: str = ""

    @property
    def nature(self) -> str:
        if self.value > 0.05:
            return "harmonious"
        if self.value < -0.05:
            return "tense"
        return "neutral"

    @property
    def contribution(self) -> float:
        share = settings()["background_score_share"] if self.background else 1.0
        return self.weight * self.value * share

    def sort_key(self) -> tuple:
        # Strongest first; names break ties so the order is deterministic.
        return (-round(self.weight, 9), self.kind, self.transit, self.aspect or "", self.natal or "")


def _round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def _aspect_value(aspect: str, transit: str, natal: str, cfg: dict) -> float:
    if aspect == "conjunction":
        tones = cfg["tones"]
        value = tones[transit] + cfg["conjunction_natal_tone_share"] * tones[natal]
        return max(-1.0, min(1.0, value))
    return cfg["aspect_values"][aspect]


def moon_exact_time(
    lon_start: float, lon_end: float, start: datetime, end: datetime, natal_lon: float, angle: float
) -> datetime | None:
    """When during [start, end] the Moon forms `angle` to `natal_lon`, or None.

    The Moon never moves retrograde and covers ~12-15 degrees a day, so a linear
    interpolation between the day's start and end positions is accurate to minutes.
    """
    span = zodiac.norm(lon_end - lon_start)
    for point in zodiac.aspect_points(natal_lon, angle):
        offset = zodiac.norm(point - lon_start)
        if offset <= span:
            return start + (end - start) * (offset / span)
    return None


def _aspect_factors(natal: dict, transits: dict, day_bounds: tuple, noon: datetime) -> list[Factor]:
    cfg = settings()
    first_house = zodiac.SIGNS.index(natal["first_house_sign"])
    start, end = day_bounds
    moon_start = ephemeris.positions(start, ["moon"])["moon"].lon
    moon_end = ephemeris.positions(end, ["moon"])["moon"].lon

    factors = []
    for transit, pos in transits.items():
        for natal_name, natal_lon in natal_points(natal).items():
            for aspect, spec in cfg["aspects"].items():
                orb = abs(zodiac.separation(pos.lon, natal_lon) - spec["angle"])
                exact_at = None
                if transit == "moon":
                    exact_at = moon_exact_time(moon_start, moon_end, start, end, natal_lon, spec["angle"])
                    if exact_at is None:
                        continue
                    hours_from_noon = abs((exact_at - noon).total_seconds()) / 3600
                    drop = 1 - cfg["moon_window_min_tightness"]
                    tightness = 1 - drop * min(hours_from_noon / 12, 1)
                else:
                    max_orb = cfg["orbs"][transit]
                    if orb > max_orb:
                        continue
                    floor = cfg["tightness_floor"]
                    tightness = floor + (1 - floor) * (1 - orb / max_orb)

                natal_weight = cfg["natal_weights"][natal_name]
                if natal_name == "moon" and not natal["birth_time_known"]:
                    natal_weight *= cfg["unknown_time_natal_moon_factor"]
                factors.append(
                    Factor(
                        kind="aspect",
                        transit=transit,
                        aspect=aspect,
                        natal=natal_name,
                        orb=orb,
                        exact_at=exact_at,
                        house=zodiac.whole_sign_house(pos.lon, first_house),
                        weight=cfg["transit_weights"][transit] * natal_weight * spec["strength"] * tightness,
                        value=_aspect_value(aspect, transit, natal_name, cfg),
                    )
                )
    return factors


def _placement_factors(natal: dict, transits: dict) -> list[Factor]:
    cfg = settings()
    first_house = zodiac.SIGNS.index(natal["first_house_sign"])
    return [
        Factor(
            kind="placement",
            transit=body,
            house=zodiac.whole_sign_house(transits[body].lon, first_house),
            weight=cfg["transit_weights"][body] * cfg["placements"]["weight"],
            value=cfg["tones"][body],
        )
        for body in cfg["placements"]["bodies"]
    ]


def _cap_slow_planets(factors: list[Factor]) -> list[Factor]:
    """Keep only the strongest slow-planet factor, as the background theme."""
    slow_planets = settings()["slow_planets"]
    slow = [f for f in factors if f.transit in slow_planets]
    if not slow:
        return factors
    keep = min(slow, key=Factor.sort_key)
    keep.background = True
    return [f for f in factors if f.transit not in slow_planets or f is keep]


def _belongs_to(f: Factor, category: dict) -> bool:
    # Placements count only through their house: a planet's own category would
    # otherwise get its tone every single day (e.g. Venus → love always positive).
    if f.house in category["houses"]:
        return True
    return f.kind == "aspect" and (f.transit in category["planets"] or f.natal in category["planets"])


def _paws(raw: float) -> int:
    cfg = settings()
    paws = 3 + 2 * math.tanh((raw - cfg["score_center"]) / cfg["score_scale"])
    return max(1, min(5, _round_half_up(paws)))


def _select(factors: list[Factor]) -> list[Factor]:
    """Top 3-5 factors, always including at least one Moon factor."""
    sel = settings()["selection"]
    ranked = sorted(factors, key=Factor.sort_key)
    selected = [f for f in ranked if f.weight >= sel["min_weight"]][: sel["max"]]
    for f in ranked:
        if len(selected) >= sel["min"]:
            break
        if f not in selected:
            selected.append(f)

    if not any(f.transit == "moon" for f in selected):
        moon_aspects = [f for f in ranked if f.transit == "moon" and f.kind == "aspect"]
        moon = moon_aspects[0] if moon_aspects else next(f for f in ranked if f.transit == "moon")
        if len(selected) >= sel["max"]:
            selected[-1] = moon
        else:
            selected.append(moon)
    return sorted(selected, key=Factor.sort_key)


def _band(score: int) -> str:
    return "low" if score <= 2 else "mid" if score == 3 else "high"


def _transit_dict(transits: dict, first_house: int) -> dict:
    return {
        name: {
            "lon": round(pos.lon, 4),
            "sign": zodiac.sign_of(pos.lon),
            "degree": round(zodiac.degree_in_sign(pos.lon), 2),
            "house": zodiac.whole_sign_house(pos.lon, first_house),
            "retrograde": pos.speed < 0,
        }
        for name, pos in transits.items()
    }


def _factor_dict(f: Factor, tz: ZoneInfo) -> dict:
    return {
        "id": f.id,
        "kind": f.kind,
        "transit": f.transit,
        "aspect": f.aspect,
        "natal": f.natal,
        "house": f.house,
        "nature": f.nature,
        "orb": None if f.orb is None else round(f.orb, 2),
        "exact_at": None if f.exact_at is None else f.exact_at.astimezone(tz).strftime("%H:%M"),
        "weight": round(f.weight, 3),
        "value": round(f.value, 2),
        "background": f.background,
        "categories": f.categories,
        "keywords": f.keywords,
    }


def compute_day(profile: Profile, day: date) -> dict[str, Any]:
    """Full engine output for one user and one local date (stored as engine_json)."""
    cfg = settings()
    kw = keywords()
    tz_name = profile.current_timezone
    tz = ZoneInfo(tz_name)
    input_hash = profile.input_hash()
    seed = hashlib.sha256(f"{input_hash}|{day.isoformat()}".encode()).hexdigest()
    rng = random.Random(int(seed[:16], 16))

    natal = compute_natal(profile)
    first_house = zodiac.SIGNS.index(natal["first_house_sign"])
    noon = local_noon(day, tz_name)
    transits = ephemeris.positions(noon, cfg["bodies"])

    factors = _aspect_factors(natal, transits, local_day_bounds(day, tz_name), noon)
    factors += _placement_factors(natal, transits)
    factors = _cap_slow_planets(factors)
    for f in factors:
        f.categories = [c for c in CATEGORIES if _belongs_to(f, cfg["categories"][c])]

    scores = {}
    raws = {}
    for c in CATEGORIES:
        contributing = [f for f in factors if c in f.categories]
        raws[c] = sum(f.contribution for f in contributing)
        scores[c] = _paws(raws[c]) if contributing else 3

    weights = cfg["overall_weights"]
    overall = _round_half_up(sum(weights[c] * scores[c] for c in CATEGORIES) / sum(weights.values()))

    selected = _select(factors)
    for i, f in enumerate(selected, start=1):
        f.id = f"f{i}"
        if f.kind == "aspect":
            f.keywords = [
                rng.choice(kw["planets"][f.transit]),
                rng.choice(kw["natal_points"][f.natal]),
                rng.choice(kw["natures"][f.nature]),
            ]
        else:
            f.keywords = [rng.choice(kw["planets"][f.transit]), rng.choice(kw["houses"][f.house])]

    moon_lon = transits["moon"].lon
    moon_sign = zodiac.sign_of(moon_lon)
    moon_house = zodiac.whole_sign_house(moon_lon, first_house)
    categories = {}
    for c in CATEGORIES:
        if any(c in f.categories for f in factors):
            words = rng.sample(kw["category_bands"][c][_band(scores[c])], 2)
        else:
            words = [rng.choice(kw["moon_signs"][moon_sign]), rng.choice(kw["houses"][moon_house])]
        categories[c] = {
            "score": scores[c],
            "raw": round(raws[c], 3),
            "keywords": words,
            "factor_ids": [f.id for f in selected if c in f.categories],
        }

    return {
        "engine_version": engine_version(),
        "input_hash": input_hash,
        "date": day.isoformat(),
        "timezone": tz_name,
        "natal": natal,
        "transits": _transit_dict(transits, first_house),
        "day": {
            "moon_sign": moon_sign,
            "moon_phase": zodiac.moon_phase(transits["sun"].lon, moon_lon),
            "overall_score": overall,
            "mira_pose": cfg["poses"][overall],
            "moon_aspect_found": any(f.transit == "moon" and f.kind == "aspect" for f in factors),
        },
        "categories": categories,
        "factors": [_factor_dict(f, tz) for f in selected],
    }
