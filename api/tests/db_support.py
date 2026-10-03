"""Test database (PostgreSQL in Docker) and a fake LLM for the service tests."""

import json
import os
import threading
import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from astrocat.settings import load_env_file

TEST_DB = "astrocat_test"
TABLES = ["sessions", "daily_readings", "birth_profiles", "users", "place_names", "places"]


def configure_test_database() -> str:
    """Point DATABASE_URL at a fresh, migrated test database; skip if PostgreSQL is not running."""
    load_env_file()
    from astrocat import db, settings

    base = make_url(settings._database_url())
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
            conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    except Exception as exc:  # pragma: no cover - environment dependent
        hint = "docker compose -f compose.yaml -f compose.dev.yaml up -d db"
        pytest.skip(f"PostgreSQL not reachable ({exc.__class__.__name__}); run: {hint}")
    finally:
        admin.dispose()

    url = base.set(database=TEST_DB).render_as_string(hide_password=False)
    os.environ["DATABASE_URL"] = url
    settings.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.session_factory.cache_clear()

    from astrocat.migrate import upgrade

    with db.get_engine().begin() as conn:
        upgrade(conn)
    return url


def truncate_all() -> None:
    from astrocat.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))


_HEADLINES = [
    ("Bright", "skies"), ("Calm", "waters"), ("Bold", "steps"), ("Gentle", "breeze"), ("Sunny", "corners"),
    ("Steady", "rhythm"), ("Lively", "sparks"), ("Cozy", "evenings"), ("Clear", "paths"), ("Golden", "moments"),
]  # fmt: skip
_ADVICE = [
    "Call someone you have not heard from in a while.",
    "Take a short walk before lunch.",
    "Tidy the drawer that annoys you most.",
    "Cook something warm for dinner tonight.",
    "Go to bed half an hour early.",
    "Write down one idea before it slips away.",
    "Ask a colleague a question you have been saving.",
    "Put on a song you loved as a teenager.",
    "Drink a glass of water and stretch for a minute.",
    "Plan one small treat for the weekend.",
]


class FakeLLM:
    """Returns valid English readings that differ every call (so repetition checks pass)."""

    model = "fake-llm"

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls: list[list[dict]] = []
        self._lock = threading.Lock()

    def chat(self, messages, schema, temperature=0.7):
        with self._lock:
            n = len(self.calls)
            self.calls.append(messages)
        if self.delay:
            time.sleep(self.delay)
        first, last = _HEADLINES[n % len(_HEADLINES)]
        return json.dumps(
            {
                "headline": f"{first} vibes and {last}",
                "summary": f"{first} hours are ahead of you today. Take the time you need and enjoy it.",
                "sections": {
                    "love": "A short message to someone close will make their day.",
                    "work": "Finish one thing before you start the next.",
                    "energy": "Your energy is steady, so pace yourself.",
                    "mood": "You may feel tender today, and that is fine.",
                },
                "advice": _ADVICE[n % len(_ADVICE)],
            }
        )
