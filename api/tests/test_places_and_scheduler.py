"""City search import/search and the background scheduler (PostgreSQL required)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from astrocat.db import DailyReading
from astrocat.places import import_places, normalize, place_count, search_places
from astrocat.scheduler import due_users, run_once

SAMPLE = Path(__file__).parent / "data" / "cities_sample.txt"


# --- places ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "norm"), [("München", "munchen"), ("Múnich", "munich"), ("Straße", "strasse"), (" Sevilla ", "sevilla")]
)
def test_normalize(name, norm):
    assert normalize(name) == norm


@pytest.fixture
def imported(sessions):
    with sessions() as db:
        assert import_places(db, SAMPLE) == 7
    return sessions


@pytest.mark.parametrize("query", ["munich", "München", "muench", "Múnich", "MUN"])
def test_search_finds_munich_by_any_name(imported, query):
    with imported() as db:
        names = [p.name for p in search_places(db, query)]
    assert "Munich" in names


def test_search_orders_by_population(imported):
    with imported() as db:
        names = [p.name for p in search_places(db, "mun")]
    assert names == ["Munich", "Münster"]  # 1.26 M before 270 k


def test_search_alternate_names_and_short_queries(imported):
    with imported() as db:
        assert [p.name for p in search_places(db, "seville")] == ["Sevilla"]
        assert [p.name for p in search_places(db, "russelsheim")] == ["Rüsselsheim"]
        assert search_places(db, "m") == []  # too short
        assert search_places(db, "%") == []  # LIKE wildcards are escaped


def test_import_replaces_existing_places(imported):
    with imported() as db:
        import_places(db, SAMPLE)
        assert place_count(db) == 7


# --- scheduler --------------------------------------------------------------------------


def readings(sessions) -> int:
    with sessions() as db:
        return db.scalar(select(func.count()).select_from(DailyReading))


@pytest.fixture
def days_ahead(monkeypatch):
    from astrocat import settings

    def set_days(n: int) -> None:
        monkeypatch.setenv("GENERATE_DAYS_AHEAD", str(n))
        settings.get_settings.cache_clear()

    yield set_days
    monkeypatch.delenv("GENERATE_DAYS_AHEAD", raising=False)
    settings.get_settings.cache_clear()


def test_scheduler_waits_for_the_local_day_to_start(sessions, make_user, fake_llm):
    # 22:02 UTC = 00:02 in Berlin (summer time): the new day has started, but not yet 00:05.
    berlin = make_user("anna", timezone="Europe/Berlin")
    london = make_user("sam", timezone="Europe/London")  # 23:02 there: its day is well under way
    now = datetime(2026, 10, 3, 22, 2, tzinfo=UTC)
    due = due_users(sessions, now)
    assert all(user != berlin for user, _ in due)
    assert [d.isoformat() for user, d in due if user == london] == ["2026-10-03", "2026-10-04", "2026-10-05"]


def test_scheduler_prepares_today_first_then_the_next_days(sessions, make_user):
    anna = make_user("anna", timezone="Europe/Berlin")
    sam = make_user("sam", timezone="Europe/London")
    due = due_users(sessions, datetime(2026, 10, 3, 9, 0, tzinfo=UTC))
    assert [(u, d.isoformat()) for u, d in due] == [
        (anna, "2026-10-03"), (sam, "2026-10-03"),
        (anna, "2026-10-04"), (sam, "2026-10-04"),
        (anna, "2026-10-05"), (sam, "2026-10-05"),
    ]  # fmt: skip


def test_scheduler_generates_missing_readings_and_skips_existing(sessions, make_user, fake_llm):
    make_user("anna", timezone="Europe/Berlin")
    make_user("sam", timezone="Europe/London")
    make_user("new", onboarded=False)
    now = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
    assert run_once(sessions, fake_llm, now) == 6  # 2 users × 3 days; the user without birth data is skipped
    assert readings(sessions) == 6
    assert run_once(sessions, fake_llm, now) == 0  # nothing left to do
    # The next morning only the new third day is missing.
    assert run_once(sessions, fake_llm, datetime(2026, 10, 4, 9, 0, tzinfo=UTC)) == 2
    assert len(fake_llm.calls) == 8


def test_days_ahead_can_be_turned_off(sessions, make_user, fake_llm, days_ahead):
    days_ahead(0)
    make_user("anna")
    assert run_once(sessions, fake_llm, datetime(2026, 10, 3, 9, 0, tzinfo=UTC)) == 1


def test_scheduler_catches_up_after_sleep(sessions, make_user, fake_llm, days_ahead):
    days_ahead(0)
    make_user("anna", timezone="Europe/Berlin")
    # The Mac slept through the night; the first run is at 07:40 local time.
    assert run_once(sessions, fake_llm, datetime(2026, 10, 4, 5, 40, tzinfo=UTC)) == 1
    with sessions() as db:
        assert db.scalar(select(DailyReading.local_date)).isoformat() == "2026-10-04"


def test_scheduler_survives_failures(sessions, make_user):
    class BrokenEngine:
        model = "broken"

        def chat(self, *args, **kwargs):
            raise RuntimeError("unexpected")

    make_user("anna")
    # An unexpected error (not an Ollama outage, which falls back) must not crash the job.
    assert run_once(sessions, BrokenEngine(), datetime(2026, 10, 3, 9, 0, tzinfo=UTC)) == 0


def test_outage_fallbacks_are_replaced_once_ollama_is_back(sessions, make_user, fake_llm, days_ahead):
    from astrocat.llm import LLMUnavailable

    class Down:
        model = "down"

        def chat(self, *args, **kwargs):
            raise LLMUnavailable("Ollama request failed (http://x): connection refused")

    days_ahead(0)
    make_user("anna")
    now = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
    assert run_once(sessions, Down(), now) == 1  # template reading while Ollama is down
    with sessions() as db:
        assert db.scalar(select(DailyReading.status)) == "fallback"
    assert run_once(sessions, fake_llm, now) == 1  # replaced once Ollama answers again
    with sessions() as db:
        rows = db.scalars(select(DailyReading)).all()
    assert [r.status for r in rows] == ["ok"]
    assert run_once(sessions, fake_llm, now) == 0


def test_fallbacks_from_failed_checks_are_not_retried(sessions, make_user, days_ahead):
    class Invalid:
        model = "invalid"

        def chat(self, *args, **kwargs):
            return "not json"

    days_ahead(0)
    make_user("anna")
    now = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
    assert run_once(sessions, Invalid(), now) == 1
    assert run_once(sessions, Invalid(), now) == 0  # the model got its 3 attempts; don't burn more
