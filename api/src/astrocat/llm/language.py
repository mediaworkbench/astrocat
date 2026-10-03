"""Language packs (names, example, checks, fallback) and localized dates."""

import hashlib
import re
from datetime import date
from functools import cache
from importlib.resources import files
from typing import Any

import yaml

from astrocat.engine.profile import LANGUAGES

# Bump when the prompt logic changes; the data files are fingerprinted automatically.
PROMPT_CODE_VERSION = "1"

_DATA = files("astrocat.llm") / "data"
_WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@cache
def pack(language: str) -> dict[str, Any]:
    if language not in LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    data = yaml.safe_load((_DATA / f"{language}.yaml").read_bytes())
    data["jargon_re"] = [re.compile(p, re.IGNORECASE) for p in data["jargon"]]
    data["forbidden_re"] = [re.compile(p, re.IGNORECASE) for p in data["forbidden"]]
    data["gendered_re"] = [re.compile(p, re.IGNORECASE) for p in data["gendered"]]
    return data


@cache
def system_prompt_template() -> str:
    return (_DATA / "system_prompt.txt").read_text(encoding="utf-8")


@cache
def prompt_version() -> str:
    digest = hashlib.sha256()
    for name in ["system_prompt.txt", *(f"{lang}.yaml" for lang in LANGUAGES)]:
        digest.update((_DATA / name).read_bytes())
    return f"{PROMPT_CODE_VERSION}+{digest.hexdigest()[:8]}"


def weekday_key(day: date) -> str:
    return _WEEKDAY_KEYS[day.weekday()]


def weekday_name(day: date, language: str) -> str:
    return pack(language)["weekdays"][day.weekday()]


def date_label(day: date, language: str) -> str:
    p = pack(language)
    return p["date_format"].format(weekday=p["weekdays"][day.weekday()], day=day.day, month=p["months"][day.month - 1])
