"""HTML review report for tuning the engine (concept §6, "Review tool")."""

import html
from collections import Counter
from collections.abc import Callable
from datetime import date, timedelta

from astrocat.engine import compute_day
from astrocat.engine.config import engine_version
from astrocat.engine.daily import CATEGORIES
from astrocat.engine.describe import describe_factor
from astrocat.engine.profile import Profile
from astrocat.llm import ReadingResult, RecentReading, generate_reading, prompt_version
from astrocat.llm.client import ChatClient

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
.reading { min-width:320px; } .reading b { display:block; margin-bottom:2px; }
.reading p { margin:2px 0; } .fb { opacity:.6; }
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


def _opening(text: str) -> str:
    return " ".join(text.lower().split()[:3])


def _reading_cell(res: ReadingResult) -> str:
    rd = res.reading
    sections = "".join(f"<p><i>{c}:</i> {html.escape(rd['sections'][c])}</p>" for c in CATEGORIES)
    cls = "reading" if res.status == "ok" else "reading fb"
    return (
        f'<td class="{cls}"><b>{html.escape(rd["headline"])}</b><p>{html.escape(rd["summary"])}</p>'
        f"{sections}<p><i>advice:</i> {html.escape(rd['advice'])}</p></td>"
    )


def _reading_flags(res: ReadingResult, earlier: list[ReadingResult]) -> list[str]:
    flags = []
    if res.status != "ok":
        flags.append("FALLBACK")
    for i, errors in enumerate(res.errors, start=1):
        flags.append(f"attempt {i} rejected: {'; '.join(errors)}")
    if res.status == "ok":
        for e in earlier:
            if e.status == "ok" and _opening(e.reading["summary"]) == _opening(res.reading["summary"]):
                flags.append(f"summary opening repeats {e.date}")
    flags.append(f"{res.duration_s}s")
    return flags


def _llm_summary(results: list[ReadingResult]) -> str:
    n = len(results)
    ok = sum(r.status == "ok" for r in results)
    first_try = sum(r.status == "ok" and r.attempts == 1 for r in results)
    durations = sorted(r.duration_s for r in results)
    return (
        f"<p>LLM: {ok}/{n} ok ({first_try} on the first attempt), {n - ok} fallback · "
        f"median {durations[n // 2]}s, max {durations[-1]}s per reading</p>"
    )


def _day_row(d: dict, res: ReadingResult | None = None, earlier: list[ReadingResult] | None = None) -> str:
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
    reading = ""
    if res is not None:
        reading = _reading_cell(res)
        flags += _reading_flags(res, earlier or [])
    return (
        f"<tr><td>{d['date']}</td>{cells}"
        f'<td class="n s{d["day"]["overall_score"]}">{d["day"]["overall_score"]}</td>'
        f"<td>{d['day']['mira_pose']}</td><td>{html.escape(moon)}</td>"
        f"<td><ul>{factors}</ul><small>{html.escape(keywords)}</small></td>{reading}"
        f'<td class="flag">{"<br>".join(html.escape(f) for f in flags)}</td></tr>'
    )


def _generate_series(
    profile: Profile, start: date, days: int, client: ChatClient, language: str | None, progress: Callable
) -> tuple[list[dict], list[ReadingResult]]:
    """Days in order, so each prompt sees the previous readings (recent-readings block)."""
    engines, readings = [], []
    for i in range(days):
        day = start + timedelta(days=i)
        recent = [
            RecentReading(r.date, r.reading["headline"], r.reading["advice"], r.reading["summary"])
            for r in readings[-3:]
            if r.status == "ok"
        ]
        engine, result = generate_reading(profile, day, client, language, recent)
        engines.append(engine)
        readings.append(result)
        status = f"{result.status} ({result.attempts}x, {result.duration_s}s)"
        progress(f"{profile.display_name} {day} {result.language}: {status}")
    return engines, readings


def render_review(
    profiles: list[Profile],
    start: date,
    days: int,
    client: ChatClient | None = None,
    language: str | None = None,
    progress: Callable[[str], None] = lambda _: None,
) -> str:
    """Engine-only report, or with readings when a client is given."""
    sections = []
    for profile in profiles:
        if client is None:
            results = [compute_day(profile, start + timedelta(days=i)) for i in range(days)]
            readings: list[ReadingResult | None] = [None] * days
        else:
            results, readings = _generate_series(profile, start, days, client, language, progress)
        natal = results[0]["natal"]
        time_note = "birth time known" if natal["birth_time_known"] else "birth time unknown (solar houses)"
        columns = ["date", *CATEGORIES, "overall", "pose", "moon", "top factors"]
        if client is not None:
            columns.append(f"reading ({readings[0].language})")
        head = "".join(f"<th>{c}</th>" for c in (*columns, "flags"))
        llm_summary = _llm_summary(readings) if client is not None else ""
        rows = "".join(
            _day_row(d, res, [r for r in readings[:i] if r is not None])
            for i, (d, res) in enumerate(zip(results, readings, strict=True))
        )
        sections.append(
            f"<h2>{html.escape(profile.display_name)}</h2>"
            f'<p class="meta">Sun in {natal["bodies"]["sun"]["sign"]}, {time_note} · {profile.current_timezone}</p>'
            + _summary(results)
            + llm_summary
            + f'<div class="wrap"><table><tr>{head}</tr>{rows}</table></div>'
        )
    end = start + timedelta(days=days - 1)
    mode = "engine only (no LLM)" if client is None else f"model {client.model} · prompt {prompt_version()}"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>AstroCat review</title><style>{_CSS}</style></head><body>"
        f"<h1>{PAW} AstroCat review</h1>"
        f'<p class="meta">{start} – {end} · engine {engine_version()} · {mode}</p>'
        + "".join(sections)
        + "</body></html>"
    )
