"""HTTP API for the AstroCat app (concept §2, §8, §9). Served under /api."""

import datetime as dt
import logging
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from astrocat import auth
from astrocat.db import BirthProfile, Place, User, get_db, session_factory
from astrocat.engine.profile import GRAMMATICAL_GENDERS, LANGUAGES
from astrocat.llm import OllamaClient
from astrocat.llm.client import ChatClient
from astrocat.places import search_places
from astrocat.readings import (
    OnboardingIncomplete,
    ReadingNotReady,
    get_or_create_reading,
    local_today,
    reading_response,
)
from astrocat.settings import get_settings, load_env_file

log = logging.getLogger(__name__)

DB = Annotated[Session, Depends(get_db)]


# --- request models ----------------------------------------------------------


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except Exception as exc:
        raise ValueError(f"unknown timezone: {value}") from exc
    return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=auth.MIN_PASSWORD_LENGTH, max_length=256)
    invite_code: str = Field(min_length=1, max_length=200)
    language: str = "en"
    timezone: str = "UTC"

    @field_validator("language")
    @classmethod
    def _language(cls, v: str) -> str:
        if v not in LANGUAGES:
            raise ValueError(f"language must be one of {LANGUAGES}")
        return v

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str) -> str:
        return _check_timezone(v)


class SettingsUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    language: str | None = None
    grammatical_gender: str | None = None
    timezone: str | None = None

    @field_validator("language")
    @classmethod
    def _language(cls, v: str | None) -> str | None:
        if v is not None and v not in LANGUAGES:
            raise ValueError(f"language must be one of {LANGUAGES}")
        return v

    @field_validator("grammatical_gender")
    @classmethod
    def _gender(cls, v: str | None) -> str | None:
        if v is not None and v not in GRAMMATICAL_GENDERS:
            raise ValueError(f"grammatical_gender must be one of {GRAMMATICAL_GENDERS}")
        return v

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str | None) -> str | None:
        return None if v is None else _check_timezone(v)


class ManualPlace(BaseModel):
    """Fallback when a birth place is not in the city list."""

    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str) -> str:
        return _check_timezone(v)


class BirthUpdate(BaseModel):
    date: dt.date
    time: dt.time | None = None  # None = unknown (noon fallback)
    place_id: int | None = None
    place: ManualPlace | None = None
    utc_offset_override: float | None = Field(default=None, ge=-14, le=14)

    @field_validator("date")
    @classmethod
    def _date(cls, v: dt.date) -> dt.date:
        if not dt.date(1900, 1, 1) <= v <= dt.date.today():
            raise ValueError("birth date must be between 1900 and today")
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=auth.MIN_PASSWORD_LENGTH, max_length=256)


# --- dependencies --------------------------------------------------------------


def _set_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        auth.COOKIE_NAME,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def current_user(
    db: DB, response: Response, token: Annotated[str | None, Cookie(alias=auth.COOKIE_NAME)] = None
) -> User:
    found = auth.session_user(db, token) if token else None
    if found is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not logged in")
    user, renewed = found
    if renewed:
        _set_cookie(response, token)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def llm_client(request: Request) -> ChatClient:
    return request.app.state.llm_client


def sessions_dep() -> Iterator[Any]:
    yield session_factory()


# --- responses -------------------------------------------------------------------


def _birth_dict(birth: BirthProfile | None) -> dict[str, Any] | None:
    if birth is None:
        return None
    return {
        "date": birth.birth_date.isoformat(),
        "time": birth.birth_time.strftime("%H:%M") if birth.birth_time else None,
        "place_name": birth.place_name,
        "place_id": birth.place_id,
        "latitude": birth.latitude,
        "longitude": birth.longitude,
        "timezone": birth.birth_timezone,
        "utc_offset_override": birth.utc_offset_override,
    }


def _me(user: User) -> dict[str, Any]:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "language": user.language,
        "grammatical_gender": user.grammatical_gender,
        "timezone": user.timezone,
        "birth": _birth_dict(user.birth),
        "onboarding_complete": user.birth is not None,
    }


def _place_dict(p: Place) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "country_code": p.country_code,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "timezone": p.timezone,
        "population": p.population,
    }


# --- routes --------------------------------------------------------------------------

router = APIRouter(prefix="/api")


@router.get("/health")
def health(db: DB) -> dict[str, str]:
    db.execute(text("select 1"))
    return {"status": "ok"}


@router.post("/auth/login")
def login(body: LoginRequest, db: DB, response: Response) -> dict[str, Any]:
    key = auth.normalize_username(body.username)
    wait = auth.login_limiter.retry_after(key)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "too many failed logins, try again later", {"Retry-After": str(wait)}
        )
    user = auth.authenticate(db, body.username, body.password)
    if user is None:
        auth.login_limiter.failed(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong username or password")
    auth.login_limiter.succeeded(key)
    _set_cookie(response, auth.create_session(db, user))
    return _me(user)


@router.get("/auth/registration")
def registration() -> dict[str, bool]:
    """Whether the app should offer "Create account" (an invite code is configured)."""
    return {"enabled": auth.registration_open()}


# Wrong invite codes count against one shared budget (the app sits behind one proxy at home).
REGISTER_LIMIT_KEY = "register"


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DB, response: Response) -> dict[str, Any]:
    if not auth.registration_open():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "registration is not enabled")
    wait = auth.login_limiter.retry_after(REGISTER_LIMIT_KEY)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too many wrong invite codes, try again later",
            {"Retry-After": str(wait)},
        )
    if not auth.invite_code_ok(body.invite_code):
        auth.login_limiter.failed(REGISTER_LIMIT_KEY)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "wrong invite code")
    username = auth.normalize_username(body.username)
    if not auth.valid_username(username):
        raise HTTPException(422, "username: 3-32 characters, letters, digits, dot, underscore or hyphen")
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "username is taken")
    user = User(
        username=username,
        password_hash=auth.hash_password(body.password),
        display_name=body.username.strip(),
        language=body.language,
        grammatical_gender="neutral",
        timezone=body.timezone,
    )
    db.add(user)
    db.commit()
    log.info("user %r registered via invite code", username)
    _set_cookie(response, auth.create_session(db, user))
    return _me(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: DB, response: Response, token: Annotated[str | None, Cookie(alias=auth.COOKIE_NAME)] = None) -> None:
    if token:
        auth.delete_session(db, token)
    response.delete_cookie(auth.COOKIE_NAME, path="/")


@router.get("/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return _me(user)


@router.put("/me/settings")
def update_settings(body: SettingsUpdate, user: CurrentUser, db: DB) -> dict[str, Any]:
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return _me(user)


@router.put("/me/birth")
def update_birth(body: BirthUpdate, user: CurrentUser, db: DB) -> dict[str, Any]:
    if (body.place_id is None) == (body.place is None):
        raise HTTPException(422, "give either place_id or place")
    if body.place_id is not None:
        found = db.get(Place, body.place_id)
        if found is None:
            raise HTTPException(422, "unknown place_id")
        place = ManualPlace(
            name=f"{found.name}, {found.country_code}",
            latitude=found.latitude,
            longitude=found.longitude,
            timezone=found.timezone,
        )
    else:
        place = body.place
    birth = user.birth or BirthProfile(user_id=user.id)
    birth.birth_date = body.date
    birth.birth_time = body.time
    birth.place_name = place.name
    birth.place_id = body.place_id
    birth.latitude = place.latitude
    birth.longitude = place.longitude
    birth.birth_timezone = place.timezone
    birth.utc_offset_override = body.utc_offset_override
    user.birth = birth
    db.commit()
    db.refresh(user)
    return _me(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChange,
    user: CurrentUser,
    db: DB,
    token: Annotated[str | None, Cookie(alias=auth.COOKIE_NAME)] = None,
) -> None:
    if not auth.verify_password(user.password_hash, body.current_password):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "current password is wrong")
    user.password_hash = auth.hash_password(body.new_password)
    db.commit()
    auth.delete_user_sessions(db, user.id, keep_token=token)  # log out other devices


@router.get("/places")
def places(user: CurrentUser, db: DB, q: Annotated[str, Query(min_length=2, max_length=80)]) -> list[dict[str, Any]]:
    return [_place_dict(p) for p in search_places(db, q)]


@router.get("/today")
def today(
    user: CurrentUser,
    client: Annotated[ChatClient, Depends(llm_client)],
    sessions: Annotated[Any, Depends(sessions_dep)],
) -> dict[str, Any]:
    day = local_today(user)
    try:
        row = get_or_create_reading(sessions, user.id, day, client)
    except OnboardingIncomplete as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "birth data missing, complete onboarding first") from exc
    except ReadingNotReady as exc:
        # The app shows Mira "reading the stars" and retries.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "reading is being generated", {"Retry-After": "5"}
        ) from exc
    return reading_response(row)


# --- app -------------------------------------------------------------------------------


def create_app(client: ChatClient | None = None, run_scheduler: bool | None = None) -> FastAPI:
    load_env_file()
    settings = get_settings()
    scheduler_on = settings.scheduler_enabled if run_scheduler is None else run_scheduler
    chat_client = client or OllamaClient()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        if scheduler_on:
            from astrocat.scheduler import start_scheduler

            scheduler = start_scheduler(session_factory(), chat_client)
        yield
        if scheduler:
            scheduler.shutdown(wait=False)

    app = FastAPI(
        title="AstroCat", version="0.1.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    app.state.llm_client = chat_client
    app.include_router(router)
    return app
