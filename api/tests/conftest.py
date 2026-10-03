from pathlib import Path

import pytest

from astrocat.engine import load_profile

DEMO = Path(__file__).parent.parent / "demo"


@pytest.fixture(params=["anna", "lucia", "sam"])
def demo_profile(request):
    return load_profile(DEMO / f"{request.param}.yaml")


@pytest.fixture
def anna():
    return load_profile(DEMO / "anna.yaml")


@pytest.fixture
def sam():
    return load_profile(DEMO / "sam.yaml")


# --- database-backed tests (PostgreSQL in Docker) ---------------------------------


@pytest.fixture(scope="session")
def database():
    from db_support import configure_test_database

    return configure_test_database()


@pytest.fixture
def sessions(database):
    from db_support import truncate_all

    from astrocat.db import session_factory

    truncate_all()
    return session_factory()


@pytest.fixture
def fake_llm():
    from db_support import FakeLLM

    return FakeLLM()


@pytest.fixture
def make_user(sessions):
    """Create a user, optionally with birth data (onboarded)."""
    from datetime import date, time

    from astrocat.auth import hash_password
    from astrocat.db import BirthProfile, User

    def make(username="anna", password="correct horse", onboarded=True, timezone="Europe/Berlin", language="en"):
        with sessions() as db:
            user = User(
                username=username,
                password_hash=hash_password(password),
                display_name=username.title(),
                language=language,
                grammatical_gender="neutral",
                timezone=timezone,
            )
            if onboarded:
                user.birth = BirthProfile(
                    birth_date=date(1991, 4, 17),
                    birth_time=time(8, 20),
                    place_name="Hamburg, DE",
                    latitude=53.5511,
                    longitude=9.9937,
                    birth_timezone="Europe/Berlin",
                )
            db.add(user)
            db.commit()
            return user.id

    return make


@pytest.fixture
def api(sessions, fake_llm):
    from fastapi.testclient import TestClient

    from astrocat.app import create_app
    from astrocat.auth import login_limiter

    login_limiter._failures.clear()
    with TestClient(create_app(client=fake_llm, run_scheduler=False)) as client:
        yield client
