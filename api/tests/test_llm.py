import json
from datetime import date

import pytest

from astrocat.engine import build_llm_payload, compute_day
from astrocat.engine.profile import LANGUAGES
from astrocat.llm import LLMUnavailable, RecentReading, generate_from_payload
from astrocat.llm.fallback import fallback_reading
from astrocat.llm.language import date_label, pack
from astrocat.llm.prompt import brief, build_messages
from astrocat.llm.validate import repair, sentences, validate

SATURDAY = date(2026, 10, 3)

GOOD = {
    "en": {
        "headline": "A cozy Saturday for you",
        "summary": "The Moon wants comfort today, and so do you. Keep your plans light.",
        "sections": {
            "love": "A short message to someone close will make their day.",
            "work": "Finish one thing before you start the next.",
            "energy": "Your energy is steady, so pace yourself.",
            "mood": "You may feel tender today, and that is fine.",
        },
        "advice": "Find a sunny spot and rest for a while.",
    },
    "es": {
        "headline": "Un sábado tranquilo para ti",
        "summary": "Hoy la Luna busca calma, y tú también. Haz planes ligeros y disfruta de lo sencillo.",
        "sections": {
            "love": "Un mensaje corto a alguien cercano le alegrará el día.",
            "work": "Termina una cosa antes de empezar la siguiente.",
            "energy": "Tu energía es estable, así que ve a tu ritmo.",
            "mood": "Quizá te sientas sensible hoy, y no pasa nada.",
        },
        "advice": "Busca un rincón con sol y descansa un rato.",
    },
    "de": {
        "headline": "Ein gemütlicher Samstag für dich",
        "summary": "Der Mond sucht heute Geborgenheit, und du auch. Plane locker und genieß die kleinen Dinge.",
        "sections": {
            "love": "Eine kurze Nachricht an einen lieben Menschen macht ihm den Tag.",
            "work": "Bring eine Sache zu Ende, bevor du die nächste anfängst.",
            "energy": "Deine Energie ist stabil, also teil sie dir gut ein.",
            "mood": "Vielleicht bist du heute empfindlich, und das ist in Ordnung.",
        },
        "advice": "Such dir ein sonniges Plätzchen und ruh dich ein bisschen aus.",
    },
}


def _with(reading, **changes):
    data = json.loads(json.dumps(reading))
    for key, value in changes.items():
        if key in data["sections"]:
            data["sections"][key] = value
        else:
            data[key] = value
    return data


class FakeClient:
    model = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.temperatures = []

    def chat(self, messages, schema, temperature=0.7):
        self.calls.append(messages)
        self.temperatures.append(temperature)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, str) else json.dumps(response)


@pytest.fixture
def payload(anna):
    return build_llm_payload(compute_day(anna, SATURDAY), anna, "en")


# --- dates ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("lang", "label"),
    [("en", "Saturday, October 3"), ("es", "sábado, 3 de octubre"), ("de", "Samstag, 3. Oktober")],
)
def test_date_label(lang, label):
    assert date_label(SATURDAY, lang) == label


# --- validation ----------------------------------------------------------


@pytest.mark.parametrize("lang", LANGUAGES)
def test_good_readings_pass(lang):
    assert validate(GOOD[lang], lang, SATURDAY, []) == []


@pytest.mark.parametrize(
    ("lang", "changes", "error"),
    [
        ("en", {"love": "Venus forms a trine to your natal Moon."}, "jargon"),
        ("de", {"work": "Der Mars steht im 10. Haus."}, "jargon"),
        ("es", {"mood": "Un trígono suave te acompaña."}, "jargon"),
        ("en", {"energy": "Watch out for an accident on the road."}, "forbidden"),
        ("de", {"work": "Investiere heute in Aktien."}, "forbidden"),
        ("es", {"energy": "Cuidado con una enfermedad."}, "forbidden"),
        ("en", {"headline": "A great Monday for you"}, "wrong weekday"),
        ("de", {"headline": "Ein guter Sonntag für dich"}, "wrong weekday"),
        ("en", {"headline": "x" * 75}, "too long"),
        ("es", {"love": "Te sientes muy valorada hoy."}, "gender"),
        ("es", {"mood": "Hoy estás tranquilo y contento."}, "gender"),
        ("es", {"mood": "Dedica un rato a ti misma."}, "gender"),
        ("es", {"mood": "Te sientes muy alegre y generosa."}, "gender"),
    ],
)
def test_validation_catches_problems(lang, changes, error):
    errors = validate(_with(GOOD[lang], **changes), lang, SATURDAY, [])
    assert any(error in e for e in errors), errors


def test_language_check():
    errors = validate(GOOD["de"], "en", SATURDAY, [])
    assert any("English" in e for e in errors)


def test_repetition_check():
    recent = [RecentReading("2026-10-02", "Something else entirely", "Find a sunny spot and rest a while.")]
    errors = validate(GOOD["en"], "en", SATURDAY, recent)
    assert any("advice is too similar" in e for e in errors)

    frame = [RecentReading("2026-10-02", "Golden paws for Friday", "Other advice.")]
    errors = validate(_with(GOOD["en"], headline="A golden Saturday for you"), "en", SATURDAY, frame)
    assert any("starts or ends like" in e for e in errors)  # same first content word, ignoring "A"

    same_opening = [RecentReading("2026-10-02", "Other", "Other advice.", "The Moon wants comfort, always.")]
    errors = validate(GOOD["en"], "en", SATURDAY, same_opening)
    assert any("starts like a recent one" in e for e in errors)


def test_sentences_do_not_split_dates_or_abbreviations():
    assert sentences("Am 3. Oktober ist es ruhig. Genieß es!") == ["Am 3. Oktober ist es ruhig.", "Genieß es!"]
    assert sentences("Achte auf ein Geräusch (z.B. Vögel). Dann ruh dich aus.") == [
        "Achte auf ein Geräusch (z.B. Vögel).",
        "Dann ruh dich aus.",
    ]


def test_repair_trims_surplus_sentences():
    long = _with(GOOD["en"], love="One. Two. Three.", advice="Rest. Then play.")
    fixed = repair(long)
    assert fixed["sections"]["love"] == "One. Two."
    assert fixed["advice"] == "Rest."


# --- fallback ------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGUAGES)
def test_fallback_covers_everything(lang):
    fb = pack(lang)["fallback"]
    for score in range(1, 6):
        for key in ("headline", "summary", "advice"):
            assert fb[key][score]
        for section in ("love", "work", "energy", "mood"):
            assert fb["sections"][section][score]


@pytest.mark.parametrize("lang", LANGUAGES)
@pytest.mark.parametrize("score", range(1, 6))
def test_fallback_readings_are_valid(payload, lang, score):
    p = json.loads(json.dumps(payload)) | {"language": lang}
    p["day"]["overall_score"] = score
    for c in p["categories"].values():
        c["score"] = score
    assert validate(fallback_reading(p, SATURDAY), lang, SATURDAY, []) == []


# --- generation flow -----------------------------------------------------


def test_ok_on_first_attempt(payload):
    result = generate_from_payload(payload, SATURDAY, FakeClient([GOOD["en"]]))
    assert (result.status, result.attempts, result.errors) == ("ok", 1, [])
    assert result.reading == repair(GOOD["en"])


def test_retry_feeds_back_errors(payload):
    client = FakeClient([_with(GOOD["en"], love="A trine helps."), GOOD["en"]])
    result = generate_from_payload(payload, SATURDAY, client)
    assert (result.status, result.attempts) == ("ok", 2)
    retry_prompt = client.calls[1][-1]["content"]
    assert "jargon" in retry_prompt and "trine" in retry_prompt
    assert client.temperatures == [0.7, 0.85]


def test_all_attempts_invalid_gives_fallback(payload):
    client = FakeClient(["not json", {"headline": "x"}, _with(GOOD["en"], mood="Natal Moon.")])
    result = generate_from_payload(payload, SATURDAY, client)
    assert (result.status, result.attempts, len(result.errors)) == ("fallback", 3, 3)
    assert validate(result.reading, "en", SATURDAY, []) == []


def test_unreachable_ollama_gives_fallback(payload):
    result = generate_from_payload(payload, SATURDAY, FakeClient([LLMUnavailable("connection refused")]))
    assert (result.status, result.attempts) == ("fallback", 1)
    assert "connection refused" in result.errors[0][0]


# --- prompt --------------------------------------------------------------


def test_brief_is_localized_and_has_no_degrees(anna):
    payload = build_llm_payload(compute_day(anna, SATURDAY), anna, "de")
    recent = [RecentReading("2026-10-02", "Gestern war schön", "Ruh dich aus.")]
    text = brief(payload, SATURDAY, recent)
    assert "Samstag, 3. Oktober" in text
    assert "Krebs" in text  # Moon sign in German
    assert "Gestern war schön" in text
    assert anna.display_name not in text  # the name invites gender guesses
    assert "°" not in text and "orb" not in text.lower()


def test_system_prompt_contains_language_and_example(payload):
    system = build_messages(payload | {"language": "es"}, SATURDAY, [])[0]["content"]
    assert "Spanish" in system and "tú" in system
    assert pack("es")["example"]["headline"] in system
