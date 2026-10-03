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


def test_scheduler_waits_for_the_local_day_to_start(sessions, make_user, fake_llm):
    # 22:02 UTC = 00:02 in Berlin (summer time): the new day has started, but not yet 00:05.
    berlin = make_user("anna", timezone="Europe/Berlin")
    london = make_user("sam", timezone="Europe/London")  # 23:02 there: its day is well under way
    now = datetime(2026, 10, 3, 22, 2, tzinfo=UTC)
    due = dict(due_users(sessions, now))
    assert berlin not in due
    assert due[london].isoformat() == "2026-10-03"


def test_scheduler_generates_missing_readings_and_skips_existing(sessions, make_user, fake_llm):
    make_user("anna", timezone="Europe/Berlin")
    make_user("sam", timezone="Europe/London")
    make_user("new", onboarded=False)
    now = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
    assert run_once(sessions, fake_llm, now) == 2  # the user without birth data is skipped
    assert readings(sessions) == 2
    assert run_once(sessions, fake_llm, now) == 0  # nothing left to do
    assert len(fake_llm.calls) == 2


def test_scheduler_catches_up_after_sleep(sessions, make_user, fake_llm):
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
