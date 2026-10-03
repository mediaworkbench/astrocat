"""HTTP API: login, sessions, onboarding, settings, places, today (PostgreSQL required)."""

from datetime import timedelta
from pathlib import Path

from sqlalchemy import update

from astrocat.auth import COOKIE_NAME
from astrocat.db import UserSession, utcnow

SAMPLE = Path(__file__).parent / "data" / "cities_sample.txt"


def login(api, username="anna", password="correct horse"):
    return api.post("/api/auth/login", json={"username": username, "password": password})


# --- auth ------------------------------------------------------------------------


def test_health(api):
    assert api.get("/api/health").json() == {"status": "ok"}


def test_login_sets_httponly_cookie(api, make_user):
    make_user()
    response = login(api, username="  Anna ")  # usernames are case- and space-insensitive
    assert response.status_code == 200
    assert response.json()["username"] == "anna"
    cookie = response.headers["set-cookie"]
    assert COOKIE_NAME in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert api.get("/api/me").status_code == 200


def test_wrong_password_and_unknown_user(api, make_user):
    make_user()
    assert login(api, password="nope").status_code == 401
    assert login(api, username="bob").status_code == 401
    assert api.get("/api/me").status_code == 401


def test_rate_limit_after_repeated_failures(api, make_user):
    make_user()
    for _ in range(5):
        assert login(api, password="nope").status_code == 401
    blocked = login(api)  # even the right password is refused for now
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_logout_ends_session(api, make_user):
    make_user()
    login(api)
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/me").status_code == 401


def test_expired_session_is_rejected(api, make_user, sessions):
    make_user()
    login(api)
    with sessions() as db:
        db.execute(update(UserSession).values(expires_at=utcnow() - timedelta(minutes=1)))
        db.commit()
    assert api.get("/api/me").status_code == 401


def test_session_is_renewed_when_half_used(api, make_user, sessions):
    make_user()
    login(api)
    with sessions() as db:
        db.execute(update(UserSession).values(expires_at=utcnow() + timedelta(days=10)))
        db.commit()
    response = api.get("/api/me")
    assert response.status_code == 200
    assert COOKIE_NAME in response.headers.get("set-cookie", "")
    with sessions() as db:
        assert db.query(UserSession).one().expires_at > utcnow() + timedelta(days=80)


def test_password_change_logs_out_other_devices(api, make_user):
    from fastapi.testclient import TestClient

    make_user()
    other = TestClient(api.app)
    login(other)
    login(api)
    assert (
        api.post("/api/me/password", json={"current_password": "wrong", "new_password": "a-new-secret"}).status_code
        == 403
    )
    assert (
        api.post("/api/me/password", json={"current_password": "correct horse", "new_password": "short"}).status_code
        == 422
    )
    ok = api.post("/api/me/password", json={"current_password": "correct horse", "new_password": "a-new-secret"})
    assert ok.status_code == 204
    assert api.get("/api/me").status_code == 200  # this device stays logged in
    assert other.get("/api/me").status_code == 401  # the other one is logged out
    assert login(api, password="a-new-secret").status_code == 200


# --- onboarding and settings -------------------------------------------------------


def test_onboarding_flow_with_city_search(api, make_user, sessions):
    from astrocat.places import import_places

    with sessions() as db:
        import_places(db, SAMPLE)
    make_user(onboarded=False)
    login(api)
    me = api.get("/api/me").json()
    assert me["onboarding_complete"] is False and me["birth"] is None

    settings = api.put(
        "/api/me/settings",
        json={"display_name": "Anna", "language": "de", "grammatical_gender": "feminine", "timezone": "Europe/Berlin"},
    )
    assert settings.status_code == 200 and settings.json()["grammatical_gender"] == "feminine"

    hits = api.get("/api/places", params={"q": "munch"}).json()
    assert hits[0]["name"] == "Munich" and hits[0]["timezone"] == "Europe/Berlin"

    birth = api.put("/api/me/birth", json={"date": "1991-04-17", "time": "08:20", "place_id": hits[0]["id"]})
    assert birth.status_code == 200
    data = birth.json()
    assert data["onboarding_complete"] is True
    assert data["birth"]["place_name"] == "Munich, DE"
    assert data["birth"]["time"] == "08:20"


def test_birth_with_manual_place_and_unknown_time(api, make_user):
    make_user(onboarded=False)
    login(api)
    response = api.put(
        "/api/me/birth",
        json={
            "date": "1995-07-23",
            "time": None,
            "place": {"name": "Tiny Village", "latitude": 51.5, "longitude": -2.6, "timezone": "Europe/London"},
        },
    )
    assert response.status_code == 200
    assert response.json()["birth"]["time"] is None


def test_validation_errors(api, make_user):
    make_user(onboarded=False)
    login(api)
    assert api.put("/api/me/settings", json={"language": "fr"}).status_code == 422
    assert api.put("/api/me/settings", json={"timezone": "Mars/Olympus"}).status_code == 422
    assert api.put("/api/me/settings", json={"grammatical_gender": "other"}).status_code == 422
    place = {"name": "X", "latitude": 1, "longitude": 1, "timezone": "UTC"}
    assert api.put("/api/me/birth", json={"date": "2999-01-01", "place": place}).status_code == 422
    assert api.put("/api/me/birth", json={"date": "1990-01-01"}).status_code == 422  # neither place nor place_id
    assert api.put("/api/me/birth", json={"date": "1990-01-01", "place_id": 1, "place": place}).status_code == 422
    assert api.put("/api/me/birth", json={"date": "1990-01-01", "place_id": 999}).status_code == 422


def test_endpoints_require_login(api):
    for method, path in [
        ("get", "/api/me"),
        ("get", "/api/today"),
        ("get", "/api/places?q=mu"),
        ("put", "/api/me/settings"),
    ]:
        assert getattr(api, method)(path, **({"json": {}} if method == "put" else {})).status_code == 401


# --- today ------------------------------------------------------------------------------


def test_today_requires_onboarding(api, make_user):
    make_user(onboarded=False)
    login(api)
    assert api.get("/api/today").status_code == 409


def test_today_generates_once_and_reuses(api, make_user, fake_llm):
    make_user()
    login(api)
    first = api.get("/api/today")
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "ok"
    assert list(body["categories"]) == ["love", "work", "energy", "mood"]  # fixed order despite JSONB
    assert list(body["reading"]["sections"]) == ["love", "work", "energy", "mood"]
    assert 1 <= body["day"]["overall_score"] <= 5
    assert body["factors"] and "weight" not in body["factors"][0]
    assert api.get("/api/today").json() == body
    assert len(fake_llm.calls) == 1


def test_changing_birth_data_or_language_gives_a_new_reading(api, make_user, fake_llm):
    make_user()
    login(api)
    first = api.get("/api/today").json()
    place = {"name": "Hamburg, DE", "latitude": 53.5511, "longitude": 9.9937, "timezone": "Europe/Berlin"}
    api.put("/api/me/birth", json={"date": "1991-04-17", "time": "08:45", "place": place})
    second = api.get("/api/today").json()
    assert len(fake_llm.calls) == 2
    assert second["generated_at"] != first["generated_at"]
    # Switching language: a new reading (the fake LLM answers in English, so it falls back).
    api.put("/api/me/settings", json={"language": "de"})
    third = api.get("/api/today").json()
    assert third["language"] == "de"
