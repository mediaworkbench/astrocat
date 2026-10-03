"""Background generation of daily readings (concept §8).

Instead of one job at midnight, a job runs every few minutes and generates
today's reading for every user whose local day has started and who has none
yet. That handles each user's timezone and catches up automatically when the
Mac was asleep.
"""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from astrocat.db import BirthProfile, User, utcnow
from astrocat.llm.client import ChatClient
from astrocat.readings import ReadingNotReady, SessionFactory, find_reading, get_or_create_reading, local_today
from astrocat.settings import get_settings

log = logging.getLogger(__name__)


def due_users(sessions: SessionFactory, now: datetime) -> list[tuple[int, date]]:
    """(user id, local day) for onboarded users whose reading for today is missing."""
    start = get_settings().generation_start
    due = []
    with sessions() as db:
        users = db.scalars(select(User).join(BirthProfile)).all()
        for user in users:
            local_time = now.astimezone(ZoneInfo(user.timezone)).time()
            day = local_today(user, now)
            if local_time >= start and find_reading(db, user, day) is None:
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
