"""Reading generation: prompt → LLM → repair → validate → retry → fallback."""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from astrocat.engine import Profile, build_llm_payload, compute_day
from astrocat.llm.client import ChatClient, LLMUnavailable
from astrocat.llm.fallback import fallback_reading
from astrocat.llm.language import date_label, prompt_version, weekday_key
from astrocat.llm.prompt import RecentReading, build_messages, retry_message
from astrocat.llm.validate import OUTPUT_SCHEMA, check_schema, repair, validate

MAX_RETRIES = 2
# Each retry gets a higher temperature: the M2 review showed that small models
# tend to repeat a rejected phrase at the same temperature.
TEMPERATURES = (0.7, 0.85, 1.0)


@dataclass
class ReadingResult:
    date: str
    language: str
    status: str  # "ok" or "fallback"
    reading: dict[str, Any]
    attempts: int
    errors: list[list[str]] = field(default_factory=list)  # per rejected attempt
    model: str = ""
    prompt_version: str = ""
    engine_version: str = ""
    duration_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def add_date_fields(payload: dict[str, Any], day: date) -> dict[str, Any]:
    """Localized date fields are added here, not in the engine (concept §7.1)."""
    return payload | {"weekday": weekday_key(day), "date_label": date_label(day, payload["language"])}


def _attempt(
    client: ChatClient, messages: list[dict[str, str]], language: str, day: date, recent, temperature: float
) -> tuple:
    raw = client.chat(messages, OUTPUT_SCHEMA, temperature)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw, None, ["output is not valid JSON"]
    errors = check_schema(parsed)
    if errors:
        return raw, None, errors
    reading = repair(parsed)
    return raw, reading, validate(reading, language, day, recent)


def generate_from_payload(
    payload: dict[str, Any],
    day: date,
    client: ChatClient,
    recent: list[RecentReading] | None = None,
    engine_version: str = "",
) -> ReadingResult:
    recent = recent or []
    language = payload["language"]
    payload = add_date_fields(payload, day)
    messages = build_messages(payload, day, recent)
    result = ReadingResult(
        date=day.isoformat(),
        language=language,
        status="fallback",
        reading={},
        attempts=0,
        model=client.model,
        prompt_version=prompt_version(),
        engine_version=engine_version,
    )
    started = time.monotonic()
    try:
        for temperature in TEMPERATURES[: 1 + MAX_RETRIES]:
            result.attempts += 1
            raw, reading, errors = _attempt(client, messages, language, day, recent, temperature)
            if reading is not None and not errors:
                result.status, result.reading = "ok", reading
                break
            result.errors.append(errors)
            messages = [*messages, {"role": "assistant", "content": raw}, retry_message(errors)]
    except LLMUnavailable as exc:
        result.errors.append([str(exc)])
    if result.status != "ok":
        result.reading = fallback_reading(payload, day)
    result.duration_s = round(time.monotonic() - started, 2)
    return result


def generate_reading(
    profile: Profile,
    day: date,
    client: ChatClient,
    language: str | None = None,
    recent: list[RecentReading] | None = None,
) -> tuple[dict[str, Any], ReadingResult]:
    """Engine output and reading for one user and day."""
    engine = compute_day(profile, day)
    payload = build_llm_payload(engine, profile, language)
    return engine, generate_from_payload(payload, day, client, recent, engine["engine_version"])
