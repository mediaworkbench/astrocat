"""Template reading used when the LLM fails or is unreachable (concept §6)."""

from datetime import date
from typing import Any

from astrocat.llm.language import pack, weekday_name


def fallback_reading(payload: dict[str, Any], day: date) -> dict[str, Any]:
    lang = payload["language"]
    p = pack(lang)
    fb = p["fallback"]
    overall = payload["day"]["overall_score"]
    values = {"weekday": weekday_name(day, lang), "moon_sign": p["signs"][payload["day"]["moon_sign"]]}
    return {
        "headline": fb["headline"][overall].format(**values),
        "summary": fb["summary"][overall].format(**values),
        "sections": {name: fb["sections"][name][c["score"]] for name, c in payload["categories"].items()},
        "advice": fb["advice"][overall],
    }
