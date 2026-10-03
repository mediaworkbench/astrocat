"""Engine configuration: tunable settings and keyword tables, plus versioning."""

import hashlib
from functools import cache
from importlib.resources import files
from typing import Any

import yaml

# Bump when the engine logic changes in a way that should regenerate readings.
ENGINE_CODE_VERSION = "1.0"

_DATA = files("astrocat.engine") / "data"


def _read(name: str) -> bytes:
    return (_DATA / name).read_bytes()


@cache
def settings() -> dict[str, Any]:
    return yaml.safe_load(_read("settings.yaml"))


@cache
def keywords() -> dict[str, Any]:
    return yaml.safe_load(_read("keywords.yaml"))


@cache
def engine_version() -> str:
    """Code version plus a fingerprint of the data files.

    Tuning settings.yaml or keywords.yaml changes the version, which changes
    every input_hash, so stale readings are never served.
    """
    digest = hashlib.sha256(_read("settings.yaml") + _read("keywords.yaml")).hexdigest()
    return f"{ENGINE_CODE_VERSION}+{digest[:8]}"
