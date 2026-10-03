"""Output schema, repair, and validation of a generated reading (concept §6, §7.2)."""

import re
from datetime import date
from difflib import SequenceMatcher
from typing import Any

from astrocat.engine.profile import LANGUAGES
from astrocat.llm.language import pack
from astrocat.llm.prompt import RecentReading

SECTIONS = ("love", "work", "energy", "mood")

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "sections": {
            "type": "object",
            "properties": {name: {"type": "string"} for name in SECTIONS},
            "required": list(SECTIONS),
        },
        "advice": {"type": "string"},
    },
    "required": ["headline", "summary", "sections", "advice"],
}

MAX_SENTENCES = {"summary": 3, "section": 2, "advice": 1}
MAX_CHARS = {"headline": 70, "summary": 400, "section": 260, "advice": 180}
SIMILARITY_LIMIT = 0.8
# Ignored when comparing the first word of headlines.
_ARTICLES = {"a", "an", "the", "your", "un", "una", "el", "la", "los", "las", "tu", "ein", "eine", "der", "die", "das"}

# A sentence ends at . ! ? or … followed by whitespace and an uppercase letter
# (or ¡ ¿) — but not after a digit ("3. Oktober") or a common abbreviation.
_SENTENCE_END = re.compile(r"(?<=[^\d\s][.!?…])\s+(?=[A-ZÁÉÍÓÚÑÄÖÜ¡¿\"'„“])")
_ABBREVIATIONS = (
    "z.B.",
    "z. B.",
    "d.h.",
    "d. h.",
    "u.a.",
    "bzw.",
    "ca.",
    "e.g.",
    "i.e.",
    "etc.",
    "p. ej.",
    "Sr.",
    "Dr.",
)
_WORD = re.compile(r"[a-záéíóúñüäöß]+")


def sentences(text: str) -> list[str]:
    parts = [s for s in _SENTENCE_END.split(text.strip()) if s]
    merged: list[str] = []
    for part in parts:
        if merged and merged[-1].endswith(_ABBREVIATIONS):
            merged[-1] += " " + part
        else:
            merged.append(part)
    return merged


def texts(reading: dict[str, Any]) -> list[str]:
    return [reading["headline"], reading["summary"], *reading["sections"].values(), reading["advice"]]


def repair(reading: dict[str, Any]) -> dict[str, Any]:
    """Trim surplus sentences instead of rejecting the whole reading for them."""

    def trim(text: str, limit: int) -> str:
        return " ".join(sentences(text)[:limit])

    return {
        "headline": reading["headline"].strip().rstrip("."),
        "summary": trim(reading["summary"], MAX_SENTENCES["summary"]),
        "sections": {k: trim(v, MAX_SENTENCES["section"]) for k, v in reading["sections"].items()},
        "advice": trim(reading["advice"], MAX_SENTENCES["advice"]),
    }


def check_schema(reading: Any) -> list[str]:
    if not isinstance(reading, dict):
        return ["output is not a JSON object"]
    errors = []
    for key in ("headline", "summary", "advice"):
        if not isinstance(reading.get(key), str) or not reading[key].strip():
            errors.append(f"'{key}' is missing or empty")
    sections = reading.get("sections")
    if not isinstance(sections, dict):
        errors.append("'sections' is missing")
    else:
        for name in SECTIONS:
            if not isinstance(sections.get(name), str) or not sections[name].strip():
                errors.append(f"section '{name}' is missing or empty")
    return errors


def _lengths(reading: dict[str, Any]) -> list[str]:
    errors = []
    if len(reading["headline"]) > MAX_CHARS["headline"]:
        errors.append(f"headline is too long ({len(reading['headline'])} characters, max 60)")
    if len(reading["summary"]) > MAX_CHARS["summary"]:
        errors.append("summary is too long")
    for name, text in reading["sections"].items():
        if len(text) > MAX_CHARS["section"]:
            errors.append(f"section '{name}' is too long")
    if len(reading["advice"]) > MAX_CHARS["advice"]:
        errors.append("advice is too long")
    return errors


def _patterns(reading: dict[str, Any], language: str, kind: str, label: str) -> list[str]:
    text = " ".join(texts(reading))
    found = sorted({m.group(0) for rx in pack(language)[f"{kind}_re"] for m in rx.finditer(text)})
    return [f"{label}: {', '.join(found)}"] if found else []


def _language(reading: dict[str, Any], language: str) -> list[str]:
    words = _WORD.findall(" ".join(texts(reading)).lower())
    scores = {lang: sum(w in set(pack(lang)["stopwords"]) for w in words) for lang in LANGUAGES}
    best = max(scores, key=scores.get)
    if scores[language] < 3 or best != language and scores[best] > scores[language]:
        return [f"the reading must be written in {pack(language)['name']}"]
    return []


def _weekdays(reading: dict[str, Any], language: str, day: date) -> list[str]:
    text = " ".join(texts(reading)).lower()
    names = pack(language)["weekdays"]
    wrong = [n for i, n in enumerate(names) if i != day.weekday() and re.search(rf"\b{n.lower()}\b", text)]
    if wrong:
        return [f"mentions the wrong weekday ({', '.join(wrong)}); today is {names[day.weekday()]}"]
    return []


def _words(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", text).lower().split()


def _headline_frame(headline: str) -> tuple[str, str]:
    """First content word and last word: the parts small models turn into formulas."""
    words = _words(headline) or [""]
    content = [w for w in words if w not in _ARTICLES] or words
    return content[0], words[-1]


def _repetition(reading: dict[str, Any], recent: list[RecentReading]) -> list[str]:
    def similar(a: str, b: str) -> bool:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= SIMILARITY_LIMIT

    def words(text: str) -> str:
        return " ".join(_words(text)[:4])

    errors = []
    first, last = _headline_frame(reading["headline"])
    for r in recent:
        r_first, r_last = _headline_frame(r.headline)
        if first == r_first or last == r_last:
            errors.append(f'headline starts or ends like a recent one ("{r.headline}"); use a new structure')
            continue
        if r.opening and words(reading["summary"]) == words(r.opening):
            errors.append(f'summary starts like a recent one ("{r.opening}")')
        if similar(reading["headline"], r.headline):
            errors.append(f'headline is too similar to a recent one ("{r.headline}")')
        if similar(reading["advice"], r.advice):
            errors.append(f'advice is too similar to a recent one ("{r.advice}")')
    return errors


def validate(reading: dict[str, Any], language: str, day: date, recent: list[RecentReading]) -> list[str]:
    """All problems of an already repaired reading; empty list = valid."""
    return (
        _lengths(reading)
        + _patterns(reading, language, "jargon", "uses astrology jargon")
        + _patterns(reading, language, "forbidden", "touches a forbidden topic")
        + _patterns(reading, language, "gendered", "assumes the reader's gender, rephrase without adjectives")
        + _language(reading, language)
        + _weekdays(reading, language, day)
        + _repetition(reading, recent)
    )
