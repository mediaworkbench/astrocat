"""Reduced payload for the LLM (concept §7.1): no degrees, orbs, or weights."""

from typing import Any

from astrocat.engine.profile import Profile

CONTRACT_VERSION = 1


def build_llm_payload(engine: dict[str, Any], profile: Profile, language: str | None = None) -> dict[str, Any]:
    natal = engine["natal"]
    day = engine["day"]
    factors = []
    for f in engine["factors"]:
        item: dict[str, Any] = {"id": f["id"], "transit": f["transit"]}
        if f["kind"] == "aspect":
            item |= {"aspect": f["aspect"], "natal": f["natal"]}
        item |= {"house": f["house"], "nature": f["nature"]}
        if f["background"]:
            item["background"] = True
        item["keywords"] = f["keywords"]
        factors.append(item)

    return {
        "contract_version": CONTRACT_VERSION,
        "date": engine["date"],
        "language": language or profile.language,
        "user": {
            "display_name": profile.display_name,
            "sun_sign": natal["bodies"]["sun"]["sign"],
            "birth_time_known": natal["birth_time_known"],
        },
        "day": {
            "moon_sign": day["moon_sign"],
            "moon_phase": day["moon_phase"],
            "overall_score": day["overall_score"],
            "mira_pose": day["mira_pose"],
        },
        "categories": {
            name: {"score": c["score"], "keywords": c["keywords"], "factor_ids": c["factor_ids"]}
            for name, c in engine["categories"].items()
        },
        "factors": factors,
    }
