"""Background generation of daily readings (concept §8).

Instead of one job at midnight, a job runs every few minutes and generates
today's reading for every user whose local day has started and who has none
yet. That handles each user's timezone and catches up automatically when the
Mac was asleep.
"""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from astrocat.db import BirthProfile, User, utcnow
from astrocat.llm.client import ChatClient
from astrocat.readings import (
    ReadingNotReady,
    SessionFactory,
    fell_back_for_outage,
    find_reading,
    get_or_create_reading,
    local_today,
    release_for_retry,
)
from astrocat.settings import get_settings

log = logging.getLogger(__name__)


def due_users(sessions: SessionFactory, now: datetime) -> list[tuple[int, date]]:
    """(user id, local day) of missing readings: today first for everyone, then the days ahead.

    A template reading caused by an Ollama outage counts as missing, so it is
    replaced once Ollama is reachable again.

    Generating the days in order also gives each reading its predecessors for
    the prompt's recent-readings block.
    """
    settings = get_settings()
    due = []
    with sessions() as db:
        users = db.scalars(select(User).join(BirthProfile)).all()
        for offset in range(settings.generate_days_ahead + 1):
            for user in users:
                if now.astimezone(ZoneInfo(user.timezone)).time() < settings.generation_start:
                    continue  # the local day has only just begun
                day = local_today(user, now) + timedelta(days=offset)
                row = find_reading(db, user, day)
                if row is None:
                    due.append((user.id, day))
                elif fell_back_for_outage(row):
                    release_for_retry(db, row.id)
                    due.append((user.id, day))
    return due


def run_once(sessions: SessionFactory, client: ChatClient, now: datetime | None = None) -> int:
    """Generate all due readings; returns how many were produced. Never raises."""
    count = 0
    for user_id, day in due_users(sessions, now or utcnow()):
        try:
            get_or_create_reading(sessions, user_id, day, client)
            count += 1
        except ReadingNotReady:
            log.info("user %s: reading for %s is being generated elsewhere", user_id, day)
        except Exception:
            log.exception("user %s: scheduled generation for %s failed", user_id, day)
    return count


def start_scheduler(sessions: SessionFactory, client: ChatClient) -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_once,
        "interval",
        minutes=settings.scheduler_interval_minutes,
        args=(sessions, client),
        id="daily-readings",
        next_run_time=utcnow(),  # also once right after start
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    log.info(
        "scheduler started (every %s min, from %s local time)",
        settings.scheduler_interval_minutes,
        settings.generation_start,
    )
    return scheduler
