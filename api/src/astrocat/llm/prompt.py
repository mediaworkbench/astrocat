"""Builds the chat messages for one reading (concept §6, "Prompt structure")."""

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from astrocat.llm.language import date_label, pack, system_prompt_template, weekday_name

TONES = {1: "difficult", 2: "a bit bumpy", 3: "steady", 4: "good", 5: "excellent"}
NATURES = {"harmonious": "supportive", "tense": "challenging", "neutral": "intense"}


@dataclass(frozen=True)
class RecentReading:
    date: str
    headline: str
    advice: str
    summary: str = ""

    @property
    def opening(self) -> str:
        """First words of the summary, used to avoid repeated openings."""
        return " ".join(self.summary.split()[:4])


def system_prompt(language: str) -> str:
    p = pack(language)
    example = json.dumps(p["example"], ensure_ascii=False, indent=2)
    return system_prompt_template().format(
        language=p["name"],
        register=p["register"],
        avoid=", ".join(f'"{phrase}"' for phrase in p["avoid"]),
        gender_hint=p["gender_hint"],
        headline_case=p["headline_case"],
        example=example,
    )


def _factor_line(f: dict[str, Any], p: dict[str, Any]) -> str:
    transit = p["planets"][f["transit"]]
    keywords = ", ".join(f["keywords"])
    if "natal" in f:
        line = f"- {transit} → your {p['planets'][f['natal']]} ({NATURES[f['nature']]}): {keywords}"
    else:
        line = f"- {transit} highlights an area of your life: {keywords}"
    if f.get("background"):
        line += " [background theme for several weeks]"
    return line


def brief(payload: dict[str, Any], day: date, recent: list[RecentReading]) -> str:
    """The user message: the LLM payload rendered as a short, localized brief.

    Planet, sign and phase names are already in the target language, so the
    model never has to translate astrology terms itself. The reader's name is
    left out on purpose: small models infer a gender from it (M2 finding).
    """
    lang = payload["language"]
    p = pack(lang)
    user, d = payload["user"], payload["day"]
    lines = [
        f"Reader's Sun sign: {p['signs'][user['sun_sign']]}",
        f"Day: {date_label(day, lang)} (weekday: {weekday_name(day, lang)})",
        f"Moon today: {p['signs'][d['moon_sign']]}, {p['moon_phases'][d['moon_phase']]}",
        f"Overall tone: {d['overall_score']}/5 ({TONES[d['overall_score']]})",
        "",
        "Sections (score → tone, keywords for inspiration):",
    ]
    for name, c in payload["categories"].items():
        lines.append(f"- {name}: {c['score']}/5 ({TONES[c['score']]}): {', '.join(c['keywords'])}")
    lines += ["", "Today's influences, strongest first:"]
    lines += [_factor_line(f, p) for f in payload["factors"]]
    if recent:
        lines += ["", "Recent readings (do not reuse their headlines, phrases or openings):"]
        for r in recent:
            line = f'- {r.date}: headline "{r.headline}", advice "{r.advice}"'
            if r.opening:
                line += f', summary started with "{r.opening}"'
            lines.append(line)
    return "\n".join(lines)


def build_messages(payload: dict[str, Any], day: date, recent: list[RecentReading]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt(payload["language"])},
        {"role": "user", "content": brief(payload, day, recent)},
    ]


def retry_message(errors: list[str]) -> dict[str, str]:
    problems = "\n".join(f"- {e}" for e in errors)
    return {
        "role": "user",
        "content": f"Your reading was rejected for these reasons:\n{problems}\nWrite a new, corrected reading.",
    }
