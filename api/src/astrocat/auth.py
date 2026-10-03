"""Passwords, sessions and login rate limiting (concept §9)."""

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from astrocat.db import User, UserSession, utcnow
from astrocat.settings import get_settings

COOKIE_NAME = "astrocat_session"
MIN_PASSWORD_LENGTH = 8

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def normalize_username(username: str) -> str:
    return username.strip().lower()


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None:
        _hasher.hash(password)  # same work as a real check, so timing doesn't reveal usernames
        return None
    if not verify_password(user.password_hash, password):
        return None
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def _token_id(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    """New session; returns the cookie token (only its hash is stored)."""
    token = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(days=get_settings().session_days)
    db.add(UserSession(id=_token_id(token), user_id=user.id, expires_at=expires))
    db.commit()
    return token


def session_user(db: Session, token: str) -> tuple[User, bool] | None:
    """User of a valid session, and whether the session was renewed.

    Sessions slide: once less than half the lifetime is left, the expiry is
    pushed out again, so phones in daily use stay logged in.
    """
    session = db.get(UserSession, _token_id(token))
    now = utcnow()
    if session is None or session.expires_at <= now:
        return None
    lifetime = timedelta(days=get_settings().session_days)
    renewed = session.expires_at - now < lifetime / 2
    if renewed:
        session.expires_at = now + lifetime
        db.commit()
    return db.get(User, session.user_id), renewed


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.id == _token_id(token)))
    db.commit()


def delete_user_sessions(db: Session, user_id: int, keep_token: str | None = None) -> None:
    """Log out everywhere (e.g. after a password change), optionally keeping the current session."""
    query = delete(UserSession).where(UserSession.user_id == user_id)
    if keep_token:
        query = query.where(UserSession.id != _token_id(keep_token))
    db.execute(query)
    db.commit()


class LoginLimiter:
    """Allows a limited number of failed logins per key (username) in a sliding window.

    In memory: fine for one api process; it resets on restart.
    """

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _window(self) -> float:
        return get_settings().login_window_minutes * 60

    def _prune(self, key: str, now: float) -> deque[float]:
        failures = self._failures[key]
        while failures and failures[0] <= now - self._window():
            failures.popleft()
        return failures

    def retry_after(self, key: str) -> int:
        """Seconds until the next attempt is allowed; 0 if allowed now."""
        with self._lock:
            now = time.monotonic()
            failures = self._prune(key, now)
            if len(failures) < get_settings().login_max_failures:
                return 0
            return int(failures[0] + self._window() - now) + 1

    def failed(self, key: str) -> None:
        with self._lock:
            self._failures[key].append(time.monotonic())

    def succeeded(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_limiter = LoginLimiter()
