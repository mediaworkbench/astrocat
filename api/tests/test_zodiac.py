import pytest

from astrocat.engine import zodiac


@pytest.mark.parametrize(
    ("lon", "sign", "degree"),
    [(0, "aries", 0), (29.99, "aries", 29.99), (30, "taurus", 0), (359.5, "pisces", 29.5), (-10, "pisces", 20)],
)
def test_signs(lon, sign, degree):
    assert zodiac.sign_of(lon) == sign
    assert zodiac.degree_in_sign(lon) == pytest.approx(degree)


@pytest.mark.parametrize(("a", "b", "expected"), [(10, 350, 20), (350, 10, 20), (0, 180, 180), (100, 220, 120)])
def test_separation(a, b, expected):
    assert zodiac.separation(a, b) == pytest.approx(expected)


def test_whole_sign_house():
    taurus = zodiac.SIGNS.index("taurus")
    assert zodiac.whole_sign_house(45, taurus) == 1  # Taurus
    assert zodiac.whole_sign_house(280, taurus) == 9  # Capricorn
    assert zodiac.whole_sign_house(15, taurus) == 12  # Aries


@pytest.mark.parametrize(
    ("elongation", "phase"),
    [
        (0, "new_moon"),
        (22.4, "new_moon"),
        (22.6, "waxing_crescent"),
        (90, "first_quarter"),
        (180, "full_moon"),
        (270, "last_quarter"),
        (340, "new_moon"),
    ],
)
def test_moon_phase(elongation, phase):
    sun = 200.0
    assert zodiac.moon_phase(sun, sun + elongation) == phase


def test_aspect_points():
    assert zodiac.aspect_points(10, 0) == [10]
    assert zodiac.aspect_points(10, 180) == [190]
    assert zodiac.aspect_points(10, 120) == [130, 250]
