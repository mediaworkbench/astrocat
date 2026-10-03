import json
import math
from dataclasses import replace
from datetime import date, time, timedelta

import pytest

from astrocat.engine import ProfileError, build_llm_payload, compute_day, compute_natal
from astrocat.engine.daily import CATEGORIES
from astrocat.engine.profile import profile_from_dict

DAY = date(2026, 10, 3)


def _keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _keys(item)


def test_natal_with_known_time_has_ascendant(anna):
    natal = compute_natal(anna)
    assert natal["houses"] == "whole_sign"
    assert natal["ascendant"] is not None
    assert natal["first_house_sign"] == natal["ascendant"]["sign"]
    assert natal["bodies"]["sun"]["sign"] == "aries"


def test_natal_with_unknown_time_uses_solar_houses(sam):
    natal = compute_natal(sam)
    assert natal["houses"] == "solar"
    assert natal["ascendant"] is None
    assert natal["first_house_sign"] == natal["bodies"]["sun"]["sign"]
    assert natal["bodies"]["sun"]["house"] == 1


def test_output_is_deterministic_and_serializable(demo_profile):
    first = compute_day(demo_profile, DAY)
    assert first == compute_day(demo_profile, DAY)
    json.dumps(first)


def test_input_hash_changes_with_birth_data(anna):
    changed = replace(anna, birth=replace(anna.birth, time=time(8, 21)))
    assert anna.input_hash() != changed.input_hash()
    assert anna.input_hash() == replace(anna, display_name="Other").input_hash()


def test_payload_contract(demo_profile):
    engine = compute_day(demo_profile, DAY)
    payload = build_llm_payload(engine, demo_profile, "es")

    assert payload["language"] == "es"
    forbidden = {"orb", "lon", "degree", "weight", "raw", "value", "exact_at"}
    assert not forbidden & set(_keys(payload)), "the LLM must not see degrees or weights"

    ids = {f["id"] for f in payload["factors"]}
    for category in payload["categories"].values():
        assert set(category["factor_ids"]) <= ids

    scores = [payload["categories"][c]["score"] for c in CATEGORIES]
    assert payload["day"]["overall_score"] == math.floor(sum(scores) / len(scores) + 0.5)


def test_invariants_over_60_days(demo_profile):
    for offset in range(60):
        engine = compute_day(demo_profile, DAY + timedelta(days=offset))
        factors = engine["factors"]
        assert 3 <= len(factors) <= 5
        assert [f["id"] for f in factors] == [f"f{i}" for i in range(1, len(factors) + 1)]
        assert any(f["transit"] == "moon" for f in factors), "always at least one Moon factor"
        assert sum(f["background"] for f in factors) <= 1
        for c in CATEGORIES:
            assert 1 <= engine["categories"][c]["score"] <= 5
            assert len(engine["categories"][c]["keywords"]) == 2


def test_moon_aspects_have_exact_time(demo_profile):
    for offset in range(10):
        for f in compute_day(demo_profile, DAY + timedelta(days=offset))["factors"]:
            is_moon_aspect = f["transit"] == "moon" and f["kind"] == "aspect"
            assert (f["exact_at"] is not None) == is_moon_aspect


def test_high_latitude():
    tromso = profile_from_dict(
        {
            "display_name": "Test",
            "language": "en",
            "current_timezone": "Europe/Oslo",
            "birth": {
                "date": "1990-12-21",
                "time": "03:00",
                "latitude": 69.65,
                "longitude": 18.96,
                "timezone": "Europe/Oslo",
            },
        }
    )
    assert compute_natal(tromso)["ascendant"] is not None
    assert compute_day(tromso, date(2026, 12, 21))["day"]["mira_pose"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"time": 875}, "quoted"),
        ({"timezone": "Mars/Olympus"}, "unknown timezone"),
        ({"latitude": 95}, "out of range"),
    ],
)
def test_profile_validation(change, message):
    data = {
        "display_name": "Test",
        "language": "en",
        "current_timezone": "Europe/Berlin",
        "birth": {"date": "1990-01-01", "latitude": 52.5, "longitude": 13.4, "timezone": "Europe/Berlin"},
    }
    data["birth"] |= change
    with pytest.raises(ProfileError, match=message):
        profile_from_dict(data)
