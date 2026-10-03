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
