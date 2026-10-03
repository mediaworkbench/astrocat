"""Command line interface: `astrocat chart | day | review`."""

import json
from datetime import date
from pathlib import Path

import click

from astrocat.engine import ProfileError, build_llm_payload, compute_day, compute_natal, load_profile
from astrocat.engine.profile import LANGUAGES


def _profile(path: str):
    try:
        return load_profile(path)
    except ProfileError as exc:
        raise click.BadParameter(str(exc), param_hint=f"profile {path}") from exc


def _echo_json(data: dict) -> None:
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


@click.group()
def main() -> None:
    """AstroCat tools: engine, readings, users, server."""
    from astrocat.settings import load_env_file

    load_env_file()


# --- service and database -------------------------------------------------------------


@main.command()
def migrate() -> None:
    """Apply database migrations."""
    from astrocat.migrate import upgrade

    upgrade()
    click.echo("Database is up to date.")


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
def serve(host: str, port: int) -> None:
    """Run the API server (with the background scheduler)."""
    import logging

    import uvicorn

    from astrocat.app import create_app

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host=host, port=port, proxy_headers=True, log_level="info")


def _ask_password() -> str:
    from astrocat.auth import MIN_PASSWORD_LENGTH

    while True:
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) >= MIN_PASSWORD_LENGTH:
            return password
        click.echo(f"At least {MIN_PASSWORD_LENGTH} characters, please.")


@main.command("create-user")
@click.argument("username")
@click.option("--display-name", help="Name shown in the app (default: the username).")
@click.option("--language", type=click.Choice(LANGUAGES), default="en", show_default=True)
@click.option("--timezone", "tz", default="Europe/Berlin", show_default=True, help="Current IANA timezone.")
def create_user(username: str, display_name: str | None, language: str, tz: str) -> None:
    """Create a user (alternative to self-registration with the invite code)."""
    from sqlalchemy import select

    from astrocat.auth import hash_password, normalize_username, valid_username
    from astrocat.db import User, session_factory

    name = normalize_username(username)
    if not valid_username(name):
        raise click.ClickException("username: 3-32 characters, letters, digits, dot, underscore or hyphen")
    with session_factory()() as db:
        if db.scalar(select(User).where(User.username == name)):
            raise click.ClickException(f"user {name!r} already exists")
        password = _ask_password()
        db.add(
            User(
                username=name,
                password_hash=hash_password(password),
                display_name=display_name or username,
                language=language,
                timezone=tz,
                grammatical_gender="neutral",
            )
        )
        db.commit()
    click.echo(f"Created user {name!r}. Birth data and the remaining settings are filled in during onboarding.")


@main.command("reset-password")
@click.argument("username")
def reset_password(username: str) -> None:
    """Set a new password and log the user out everywhere."""
    from sqlalchemy import select

    from astrocat.auth import delete_user_sessions, hash_password, normalize_username
    from astrocat.db import User, session_factory

    with session_factory()() as db:
        user = db.scalar(select(User).where(User.username == normalize_username(username)))
        if user is None:
            raise click.ClickException(f"no user {username!r}")
        user.password_hash = hash_password(_ask_password())
        db.commit()
        delete_user_sessions(db, user.id)
    click.echo("Password changed; all sessions of this user were logged out.")


@main.group()
def places() -> None:
    """Birth-place search data (GeoNames)."""


@places.command("import")
@click.option("--file", "source", help="Local GeoNames file instead of downloading cities1000.")
def places_import(source: str | None) -> None:
    """Load the city list (downloads ~10 MB from geonames.org once)."""
    from astrocat.db import session_factory
    from astrocat.places import import_places

    with session_factory()() as db:
        count = import_places(db, source)
    click.echo(f"Imported {count} places. Data: GeoNames (CC BY 4.0), https://www.geonames.org/")


# --- engine and readings ----------------------------------------------------------------


@main.command()
@click.option("--profile", "profile_path", required=True, type=click.Path(exists=True, dir_okay=False))
def chart(profile_path: str) -> None:
    """Print the natal chart as JSON."""
    _echo_json(compute_natal(_profile(profile_path)))


@main.command()
@click.option("--profile", "profile_path", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--date", "day", type=click.DateTime(["%Y-%m-%d"]), help="Local date (default: today).")
@click.option("--payload", is_flag=True, help="Print the reduced LLM payload instead of the full output.")
@click.option("--lang", type=click.Choice(LANGUAGES), help="Payload language (default: the profile's).")
def day(profile_path: str, day, payload: bool, lang: str | None) -> None:
    """Print the engine output (or LLM payload) for one day as JSON."""
    profile = _profile(profile_path)
    target = day.date() if day else date.today()
    result = compute_day(profile, target)
    _echo_json(build_llm_payload(result, profile, lang) if payload else result)


@main.command()
@click.option("--profile", "profile_path", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--date", "day", type=click.DateTime(["%Y-%m-%d"]), help="Local date (default: today).")
@click.option("--lang", type=click.Choice(LANGUAGES), help="Reading language (default: the profile's).")
@click.option("--model", help="Ollama model (default: $OLLAMA_MODEL or gemma4:e4b).")
def reading(profile_path: str, day, lang: str | None, model: str | None) -> None:
    """Generate Mira's reading for one day (needs Ollama)."""
    from astrocat.llm import OllamaClient, generate_reading

    profile = _profile(profile_path)
    target = day.date() if day else date.today()
    _engine, result = generate_reading(profile, target, OllamaClient(model=model), lang)
    _echo_json(result.to_dict())


@main.command()
@click.option("--profile", "profile_paths", required=True, multiple=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--from", "start", type=click.DateTime(["%Y-%m-%d"]), help="First date (default: today).")
@click.option("--days", default=14, show_default=True, type=click.IntRange(1, 366))
@click.option("--engine-only", is_flag=True, help="Skip the LLM (fast tuning of the engine).")
@click.option(
    "--lang", type=click.Choice(LANGUAGES), help="Reading language for all profiles (default: each profile's)."
)
@click.option("--model", help="Ollama model (default: $OLLAMA_MODEL or gemma4:e4b).")
@click.option("--out", default="review.html", show_default=True, type=click.Path(dir_okay=False))
def review(
    profile_paths: tuple[str, ...], start, days: int, engine_only: bool, lang: str | None, model: str | None, out: str
) -> None:
    """Render a multi-day HTML review report."""
    from astrocat.llm import OllamaClient
    from astrocat.review import render_review

    profiles = [_profile(p) for p in profile_paths]
    first = start.date() if start else date.today()
    client = None if engine_only else OllamaClient(model=model)
    html = render_review(profiles, first, days, client, lang, progress=lambda msg: click.echo(msg, err=True))
    Path(out).write_text(html, encoding="utf-8")
    click.echo(f"Wrote {out}")
