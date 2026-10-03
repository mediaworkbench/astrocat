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
    """AstroCat engine tools."""


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
