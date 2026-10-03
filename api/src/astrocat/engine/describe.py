"""Plain English descriptions of factors, for the review report.

The localized "Why Mira says this" texts come later (M2/M4) via i18n templates.
"""


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def describe_factor(f: dict) -> str:
    transit = f["transit"].capitalize()
    if f["kind"] == "placement":
        text = f"{transit} in your {_ordinal(f['house'])} house"
    else:
        natal = "Ascendant" if f["natal"] == "ascendant" else f"natal {f['natal'].capitalize()}"
        text = f"{transit} {f['aspect']} {natal} ({_ordinal(f['house'])} house)"
        if f["exact_at"]:
            text += f", exact {f['exact_at']}"
    if f["background"]:
        text += " · background"
    return text
