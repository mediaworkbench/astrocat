"""Daily readings in the database: get or create, without duplicate LLM calls (concept §8)."""

import logging
import threading
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from astrocat.db import BirthProfile, DailyReading, User, utcnow
from astrocat.engine.daily import CATEGORIES
from astrocat.engine.profile import BirthData, Profile
from astrocat.llm import RecentReading, generate_reading
from astrocat.llm.client import UNAVAILABLE_PREFIX, ChatClient
from astrocat.settings import get_settings

log = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]

# Ollama runs one model on the Mac; generating one reading at a time keeps the
# scheduler and on-demand requests from competing for it.
_generation_lock = threading.Lock()


class ReadingNotReady(Exception):
    """Another request is still generating this reading."""


class OnboardingIncomplete(Exception):
    """The user has no birth data yet."""


def profile_for(user: User, birth: BirthProfile) -> Profile:
    return Profile(
        display_name=user.display_name,
        language=user.language,
        current_timezone=user.timezone,
        grammatical_gender=user.grammatical_gender,
        birth=BirthData(
            date=birth.birth_date,
            time=birth.birth_time,
            place=birth.place_name,
            latitude=birth.latitude,
            longitude=birth.longitude,
            timezone=birth.birth_timezone,
            utc_offset_override=birth.utc_offset_override,
        ),
    )


def local_today(user: User, now: datetime | None = None) -> date:
    return (now or utcnow()).astimezone(ZoneInfo(user.timezone)).date()


def recent_readings(db: Session, user_id: int, language: str, before: date, limit: int = 3) -> list[RecentReading]:
    """The user's last readings in this language, for the prompt's recent-readings block."""
    rows = db.scalars(
        select(DailyReading)
        .where(
            DailyReading.user_id == user_id,
            DailyReading.language == language,
            DailyReading.local_date < before,
            DailyReading.status == "ok",
        )
        .order_by(DailyReading.local_date.desc(), DailyReading.updated_at.desc())
        .limit(limit)
    )
    return [
        RecentReading(
            r.local_date.isoformat(), r.reading_json["headline"], r.reading_json["advice"], r.reading_json["summary"]
        )
        for r in rows
    ]


def fell_back_for_outage(row: DailyReading) -> bool:
    """A template reading because Ollama was unreachable, not because the model failed the checks."""
    return row.status == "fallback" and any(
        UNAVAILABLE_PREFIX in str(reason) for attempt in (row.errors or []) for reason in attempt
    )


def release_for_retry(db: Session, reading_id: int) -> None:
    """Mark a reading as failed, so the next get_or_create_reading generates it again right away."""
    db.execute(update(DailyReading).where(DailyReading.id == reading_id).values(status="failed", updated_at=utcnow()))
    db.commit()


def find_reading(db: Session, user: User, day: date) -> DailyReading | None:
    """The finished reading for the user's current settings, if any."""
    if user.birth is None:
        return None
    key = profile_for(user, user.birth).input_hash()
    return db.scalar(
        select(DailyReading).where(
            DailyReading.user_id == user.id,
            DailyReading.local_date == day,
            DailyReading.language == user.language,
            DailyReading.input_hash == key,
            DailyReading.status.in_(("ok", "fallback")),
        )
    )


def _claim(db: Session, user: User, day: date, input_hash: str) -> tuple[int, bool]:
    """Insert a `generating` row for the key; returns (row id, whether we own it)."""
    stmt = (
        insert(DailyReading)
        .values(
            user_id=user.id,
            local_date=day,
            language=user.language,
            input_hash=input_hash,
            status="generating",
            attempts=0,
        )
        .on_conflict_do_nothing(constraint="uq_reading_key")
        .returning(DailyReading.id)
    )
    new_id = db.scalar(stmt)
    db.commit()
    if new_id is not None:
        return new_id, True
    existing = db.scalar(
        select(DailyReading.id).where(
            DailyReading.user_id == user.id,
            DailyReading.local_date == day,
            DailyReading.language == user.language,
            DailyReading.input_hash == input_hash,
        )
    )
    return existing, False


def _take_over_if_stale(db: Session, reading_id: int) -> bool:
    """Claim a row nobody is working on: failed, or `generating` but abandoned (e.g. after a crash)."""
    stale_before = utcnow() - timedelta(minutes=get_settings().stale_generation_minutes)
    taken = db.scalar(
        update(DailyReading)
        .where(
            DailyReading.id == reading_id,
            or_(
                DailyReading.status == "failed",
                and_(DailyReading.status == "generating", DailyReading.updated_at < stale_before),
            ),
        )
        .values(updated_at=utcnow(), status="generating")
        .returning(DailyReading.id)
    )
    db.commit()
    return taken is not None


def _generate(sessions: SessionFactory, reading_id: int, client: ChatClient) -> None:
    with sessions() as db:
        row = db.get(DailyReading, reading_id)
        user = db.get(User, row.user_id)
        profile = profile_for(user, user.birth)
        recent = recent_readings(db, user.id, row.language, row.local_date)
        day, language = row.local_date, row.language
    try:
        with _generation_lock:
            engine, result = generate_reading(profile, day, client, language, recent)
    except Exception:
        log.exception("reading generation failed (reading %s)", reading_id)
        with sessions() as db:
            db.execute(
                update(DailyReading).where(DailyReading.id == reading_id).values(status="failed", updated_at=utcnow())
            )
            db.commit()
        raise
    with sessions() as db:
        db.execute(
            update(DailyReading)
            .where(DailyReading.id == reading_id)
            .values(
                status=result.status,
                engine_json=engine,
                reading_json=result.reading,
                attempts=result.attempts,
                errors=result.errors,
                model=result.model,
                prompt_version=result.prompt_version,
                engine_version=result.engine_version,
                duration_s=result.duration_s,
                updated_at=utcnow(),
            )
        )
        db.commit()
    log.info(
        "reading %s for user %s on %s: %s after %s attempt(s)", reading_id, user.id, day, result.status, result.attempts
    )


def get_or_create_reading(
    sessions: SessionFactory, user_id: int, day: date, client: ChatClient, wait_seconds: float | None = None
) -> DailyReading:
    """The user's reading for `day` in their current language and settings.

    Exactly one caller generates it; concurrent callers wait for that result.
    Raises ReadingNotReady if waiting takes longer than `wait_seconds`.
    """
    wait_seconds = get_settings().wait_for_generation_seconds if wait_seconds is None else wait_seconds
    with sessions() as db:
        user = db.get(User, user_id)
        if user is None or user.birth is None:
            raise OnboardingIncomplete
        input_hash = profile_for(user, user.birth).input_hash()
        reading_id, owner = _claim(db, user, day, input_hash)

    deadline = time.monotonic() + wait_seconds
    while True:
        if owner:
            _generate(sessions, reading_id, client)
        with sessions() as db:
            row = db.get(DailyReading, reading_id)
            if row.status in ("ok", "fallback"):
                return row
            owner = _take_over_if_stale(db, reading_id)
        if owner:
            continue
        if time.monotonic() >= deadline:
            raise ReadingNotReady
        time.sleep(0.5)


def reading_response(row: DailyReading) -> dict[str, Any]:
    """What the app needs for the Today screen (concept §2, §4)."""
    engine = row.engine_json
    reading = row.reading_json
    # JSONB does not keep key order, so the category order is restored here.
    return {
        "date": row.local_date.isoformat(),
        "language": row.language,
        "status": row.status,
        "reading": {
            "headline": reading["headline"],
            "summary": reading["summary"],
            "sections": {name: reading["sections"][name] for name in CATEGORIES},
            "advice": reading["advice"],
        },
        "day": {k: engine["day"][k] for k in ("moon_sign", "moon_phase", "overall_score", "mira_pose")},
        "categories": {name: {"score": engine["categories"][name]["score"]} for name in CATEGORIES},
        "birth_time_known": engine["natal"]["birth_time_known"],
        "sun_sign": engine["natal"]["bodies"]["sun"]["sign"],
        # For "Why Mira says this" (texts are localized in the app, M4).
        "factors": [
            {k: f[k] for k in ("id", "kind", "transit", "aspect", "natal", "house", "nature", "exact_at", "background")}
            for f in engine["factors"]
        ],
        "generated_at": row.updated_at.isoformat(),
    }
