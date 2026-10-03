"""Service configuration from environment variables (see .env.example)."""

import os
from dataclasses import dataclass
from datetime import time
from functools import cache
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    session_days: int
    cookie_secure: bool
    scheduler_enabled: bool
    scheduler_interval_minutes: int
    # A user's reading for a new local day is generated from this local time on.
    generation_start: time
    login_max_failures: int
    login_window_minutes: int
    # A "generating" row older than this is considered abandoned (e.g. after a crash).
    stale_generation_minutes: int
    # How long a request waits for a reading another request is generating.
    wait_for_generation_seconds: int
    # Invite code for self-registration in the app; empty = registration off (accounts only via the CLI).
    registration_code: str


def load_env_file() -> None:
    """Development convenience: read the repo's .env (cwd or a parent) without overriding real env vars.

    In Docker, compose passes the variables, and no .env file exists in the container.
    """
    for folder in (Path.cwd(), *Path.cwd().parents):
        path = folder / ".env"
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                key, sep, value = line.partition("=")
                if sep and not key.strip().startswith("#"):
                    os.environ.setdefault(key.strip(), value.strip())
            return


def _database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    # On the Mac: the dev database published by compose.dev.yaml.
    password = os.environ.get("POSTGRES_PASSWORD", "astrocat")
    return f"postgresql+psycopg://astrocat:{password}@localhost:55432/astrocat"


@cache
def get_settings() -> Settings:
    return Settings(
        database_url=_database_url(),
        session_days=int(os.environ.get("SESSION_DAYS", "90")),
        # Plain HTTP on the home network for the MVP (concept §9); set to true once HTTPS exists.
        cookie_secure=_bool("COOKIE_SECURE", False),
        scheduler_enabled=_bool("SCHEDULER_ENABLED", True),
        scheduler_interval_minutes=int(os.environ.get("SCHEDULER_INTERVAL_MINUTES", "15")),
        generation_start=time.fromisoformat(os.environ.get("GENERATION_START", "00:05")),
        login_max_failures=int(os.environ.get("LOGIN_MAX_FAILURES", "5")),
        login_window_minutes=int(os.environ.get("LOGIN_WINDOW_MINUTES", "15")),
        stale_generation_minutes=int(os.environ.get("STALE_GENERATION_MINUTES", "5")),
        wait_for_generation_seconds=int(os.environ.get("WAIT_FOR_GENERATION_SECONDS", "90")),
        registration_code=os.environ.get("REGISTRATION_CODE", "").strip(),
    )
