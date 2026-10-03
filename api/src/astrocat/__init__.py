"""AstroCat: daily horoscopes, delivered by a cat."""


def main() -> None:
    from astrocat.cli import main as cli

    cli()
