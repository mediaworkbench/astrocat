"""Run database migrations from code (container start, CLI, tests)."""

from importlib.resources import files

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(files("astrocat") / "migrations"))
    return config


def upgrade(connection: Connection | None = None) -> None:
    config = alembic_config()
    if connection is not None:
        config.attributes["connection"] = connection
    command.upgrade(config, "head")
