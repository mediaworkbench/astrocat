"""HTML review report for tuning the engine (concept §6, "Review tool")."""

import html
from collections import Counter
from datetime import date, timedelta

from astrocat.engine import compute_day
from astrocat.engine.config import engine_version
from astrocat.engine.daily import CATEGORIES
from astrocat.engine.describe import describe_factor
from astrocat.engine.profile import Profile

PAW = "🐾"

_CSS = """
:root { --bg:#fbfaff; --fg:#1d1b2e; --muted:#6b6880; --line:#e4e1f0; --card:#fff;
        --warn:#b4530a; --low:#c2410c; --high:#15803d; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14121f; --fg:#ecebf5; --muted:#a19eb8; --line:#2d2a40; --card:#1c1a2b;
          --warn:#f59e0b; --low:#fb923c; --high:#4ade80; }
}
body { background:var(--bg); color:var(--fg); font:14px/1.45 system-ui, sans-serif; margin:0; padding:16px; }
h1 { font-size:20px; margin:0 0 4px; } h2 { font-size:17px; margin:32px 0 8px; }
.meta { color:var(--muted); margin-bottom:16px; }
.wrap { overflow-x:auto; }
table { border-collapse:collapse; background:var(--card); width:100%; }
th, td { border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }
th { font-weight:600; color:var(--muted); white-space:nowrap; }
td.n { text-align:center; font-variant-numeric:tabular-nums; }
.s1, .s2 { color:var(--low); font-weight:600; } .s4, .s5 { color:var(--high); font-weight:600; }
.flag { color:var(--warn); }
ul { margin:0; padding-left:16px; }
.dist td { text-align:center; }
"""


def _summary(days: list[dict]) -> str:
    rows = []
    for c in CATEGORIES:
        counts = Counter(d["categories"][c]["score"] for d in days)
        rows.append((c, [counts.get(s, 0) for s in range(1, 6)]))
    overall = Counter(d["day"]["overall_score"] for d in days)
    rows.append(("overall", [overall.get(s, 0) for s in range(1, 6)]))
    body = "".join(f"<tr><th>{name}</th>" + "".join(f"<td>{n}</td>" for n in counts) + "</tr>" for name, counts in rows)
    poses = Counter(d["day"]["mira_pose"] for d in days)
    pose_text = ", ".join(f"{p} {n}" for p, n in sorted(poses.items(), key=lambda x: -x[1]))
    moonless = sum(not d["day"]["moon_aspect_found"] for d in days)
    return (
        '<div class="wrap"><table class="dist"><tr><th>paws</th>'
        + "".join(f"<th>{s}</th>" for s in range(1, 6))
        + f"</tr>{body}</table></div>"
        f"<p>Poses: {html.escape(pose_text)} · Days without a Moon aspect: {moonless}/{len(days)}</p>"
    )


def _day_row(d: dict) -> str:
    flags = []
    if not d["day"]["moon_aspect_found"]:
        flags.append("no Moon aspect → placement")
    for c in CATEGORIES:
        if not d["categories"][c]["factor_ids"]:
            flags.append(f"{c}: no selected factor")
    cells = "".join(
        f'<td class="n s{d["categories"][c]["score"]}">{d["categories"][c]["score"]}</td>' for c in CATEGORIES
    )
    factors = "".join(f"<li>{html.escape(describe_factor(f))}</li>" for f in d["factors"])
    keywords = "; ".join(f"{c}: {', '.join(d['categories'][c]['keywords'])}" for c in CATEGORIES)
    moon = f"{d['day']['moon_sign']} · {d['day']['moon_phase'].replace('_', ' ')}"
    return (
        f"<tr><td>{d['date']}</td>{cells}"
        f'<td class="n s{d["day"]["overall_score"]}">{d["day"]["overall_score"]}</td>'
        f"<td>{d['day']['mira_pose']}</td><td>{html.escape(moon)}</td>"
        f"<td><ul>{factors}</ul><small>{html.escape(keywords)}</small></td>"
        f'<td class="flag">{html.escape("; ".join(flags))}</td></tr>'
    )


def render_review(profiles: list[Profile], start: date, days: int) -> str:
    sections = []
    for profile in profiles:
        results = [compute_day(profile, start + timedelta(days=i)) for i in range(days)]
        natal = results[0]["natal"]
        time_note = "birth time known" if natal["birth_time_known"] else "birth time unknown (solar houses)"
        head = "".join(
            f"<th>{c}</th>" for c in ("date", *CATEGORIES, "overall", "pose", "moon", "top factors", "flags")
        )
        sections.append(
            f"<h2>{html.escape(profile.display_name)}</h2>"
            f'<p class="meta">Sun in {natal["bodies"]["sun"]["sign"]}, {time_note} · {profile.current_timezone}</p>'
            + _summary(results)
            + f'<div class="wrap"><table><tr>{head}</tr>'
            + "".join(_day_row(d) for d in results)
            + "</table></div>"
        )
    end = start + timedelta(days=days - 1)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>AstroCat engine review</title><style>{_CSS}</style></head><body>"
        f"<h1>{PAW} AstroCat engine review</h1>"
        f'<p class="meta">{start} – {end} · engine {engine_version()} · engine only (no LLM)</p>'
        + "".join(sections)
        + "</body></html>"
    )
