"""Reading storage: one generation per key, waiting, take-over, recent readings (PostgreSQL required)."""

import threading
from datetime import date, timedelta

import pytest
from db_support import FakeLLM
from sqlalchemy import func, select

from astrocat.db import DailyReading, User, utcnow
from astrocat.readings import ReadingNotReady, find_reading, get_or_create_reading, profile_for

DAY = date(2026, 10, 3)


def count_rows(sessions) -> int:
    with sessions() as db:
        return db.scalar(select(func.count()).select_from(DailyReading))


def test_reading_is_stored_with_metadata(sessions, make_user, fake_llm):
    user_id = make_user()
    row = get_or_create_reading(sessions, user_id, DAY, fake_llm)
    assert row.status == "ok"
    assert row.attempts == 1 and row.model == "fake-llm"
    assert row.prompt_version and row.engine_version and row.duration_s is not None
    assert row.engine_json["date"] == DAY.isoformat()
    assert row.reading_json["headline"]


def test_concurrent_requests_make_one_llm_call(sessions, make_user):
    user_id = make_user()
    slow = FakeLLM(delay=0.5)
    results = []

    def request():
        results.append(get_or_create_reading(sessions, user_id, DAY, slow).id)

    threads = [threading.Thread(target=request) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(slow.calls) == 1
    assert len(set(results)) == 1
    assert count_rows(sessions) == 1


def test_waiting_times_out_while_another_request_generates(sessions, make_user, fake_llm):
    user_id = make_user()
    with sessions() as db:
        user = db.get(User, user_id)
        key = profile_for(user, user.birth).input_hash()
        db.add(
            DailyReading(
                user_id=user_id, local_date=DAY, language="en", input_hash=key, status="generating", attempts=0
            )
        )
        db.commit()
    with pytest.raises(ReadingNotReady):
        get_or_create_reading(sessions, user_id, DAY, fake_llm, wait_seconds=0.6)
    assert fake_llm.calls == []


def test_abandoned_generation_is_taken_over(sessions, make_user, fake_llm):
    user_id = make_user()
    with sessions() as db:
        user = db.get(User, user_id)
        key = profile_for(user, user.birth).input_hash()
        old = utcnow() - timedelta(minutes=30)
        db.add(
            DailyReading(
                user_id=user_id,
                local_date=DAY,
                language="en",
                input_hash=key,
                status="generating",
                attempts=0,
                updated_at=old,
            )
        )
        db.commit()
    row = get_or_create_reading(sessions, user_id, DAY, fake_llm, wait_seconds=2)
    assert row.status == "ok"
    assert len(fake_llm.calls) == 1
    assert count_rows(sessions) == 1


def test_failed_generation_is_retried_immediately(sessions, make_user, fake_llm):
    user_id = make_user()
    with sessions() as db:
        user = db.get(User, user_id)
        key = profile_for(user, user.birth).input_hash()
        db.add(
            DailyReading(user_id=user_id, local_date=DAY, language="en", input_hash=key, status="failed", attempts=0)
        )
        db.commit()
    assert get_or_create_reading(sessions, user_id, DAY, fake_llm, wait_seconds=1).status == "ok"


def test_recent_readings_come_from_the_database(sessions, make_user, fake_llm):
    user_id = make_user()
    headlines = []
    for offset in range(4):
        row = get_or_create_reading(sessions, user_id, DAY + timedelta(days=offset), fake_llm)
        headlines.append(row.reading_json["headline"])
    last_prompt = fake_llm.calls[-1][1]["content"]  # the brief of the 4th day
    assert "Recent readings" in last_prompt
    for previous in headlines[:3]:
        assert previous in last_prompt
    first_prompt = fake_llm.calls[0][1]["content"]
    assert "Recent readings" not in first_prompt


def test_find_reading_respects_current_settings(sessions, make_user, fake_llm):
    user_id = make_user()
    get_or_create_reading(sessions, user_id, DAY, fake_llm)
    with sessions() as db:
        user = db.get(User, user_id)
        assert find_reading(db, user, DAY) is not None
        user.language = "de"  # not committed: only checks the lookup key
        assert find_reading(db, user, DAY) is None
