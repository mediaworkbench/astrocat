"""Self-registration with an invite code (PostgreSQL required)."""

import pytest

from astrocat import settings

CODE = "stardust-42"


@pytest.fixture
def invite(monkeypatch):
    """Configure an invite code for one test; the settings cache is reset before and after."""

    def set_code(code: str) -> None:
        monkeypatch.setenv("REGISTRATION_CODE", code)
        settings.get_settings.cache_clear()

    yield set_code
    monkeypatch.delenv("REGISTRATION_CODE", raising=False)
    settings.get_settings.cache_clear()


def register(api, **changes):
    body = {
        "username": "Lucia",
        "password": "a-long-secret",
        "invite_code": CODE,
        "language": "es",
        "timezone": "Europe/Madrid",
    }
    return api.post("/api/auth/register", json=body | changes)


def test_registration_is_off_without_a_code(api, invite):
    invite("")
    assert api.get("/api/auth/registration").json() == {"enabled": False}
    assert register(api).status_code == 404


def test_register_logs_in_and_starts_onboarding(api, invite):
    invite(CODE)
    assert api.get("/api/auth/registration").json() == {"enabled": True}
    response = register(api)
    assert response.status_code == 201
    me = response.json()
    assert me["username"] == "lucia"  # stored lowercase
    assert me["display_name"] == "Lucia"
    assert me["language"] == "es" and me["timezone"] == "Europe/Madrid"
    assert me["onboarding_complete"] is False
    assert api.get("/api/me").status_code == 200  # logged in right away
    api.post("/api/auth/logout")
    assert api.post("/api/auth/login", json={"username": "lucia", "password": "a-long-secret"}).status_code == 200


def test_wrong_code_is_rejected_and_rate_limited(api, invite):
    invite(CODE)
    for _ in range(5):
        assert register(api, invite_code="guess").status_code == 403
    blocked = register(api)  # even the right code waits now
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_username_rules_and_duplicates(api, invite, make_user):
    invite(CODE)
    make_user("anna")
    assert register(api, username="Anna").status_code == 409
    for bad in ["ab", "has space", "-dash", "ü-mlaut", "x" * 33]:
        assert register(api, username=bad).status_code == 422, bad
    assert register(api, password="short").status_code == 422
    assert register(api, language="fr").status_code == 422
    assert register(api, timezone="Mars/Olympus").status_code == 422


def test_code_whitespace_is_ignored(api, invite):
    invite(CODE)
    assert register(api, invite_code=f"  {CODE} ").status_code == 201
