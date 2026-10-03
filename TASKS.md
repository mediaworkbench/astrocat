# Tasks — M1: Engine as CLI ✅

Goal (see [concept.md](concept.md) §5, §7.1, §13): birth data + date → deterministic engine JSON and LLM payload, usable from the command line, with tests and an engine-only review report.

**Done when**
- `astrocat day` produces the engine output and the LLM payload (§7.1) for any profile and date.
- Unit tests pass against known reference values; the noon fallback for unknown birth times works.
- `astrocat review --engine-only` over 30 days shows varied scores and poses for the demo profiles.

---

## Setup

- [x] Python project in `api/` (uv, Python 3.12, src layout, package `astrocat`, license AGPL-3.0-only)
- [x] Dependencies: `libephemeris`, `pyyaml`, `click`; dev: `pytest`, `ruff`
- [x] Verify `libephemeris` API, offline behavior, and reference values (J2000: Sun 280.37°, Moon 223.32°)
- [x] Root `.gitignore` (`.venv`, caches, review output)

## Engine

- [x] **Profiles:** YAML birth profile model (display name, language, birth date, optional birth time, place, lat/lon, IANA timezone, optional UTC offset override, current timezone)
- [x] **Time conversion:** local birth clock time → UTC via `zoneinfo`; manual offset override; noon fallback when the time is unknown
- [x] **Ephemeris wrapper:** positions + speeds for Sun–Pluto, Ascendant; network policy `sealed` (no downloads at runtime)
- [x] **Natal chart:** bodies with sign, degree, Whole Sign house, retrograde flag; Ascendant only when the time is known; solar houses otherwise
- [x] **Transit chart:** local noon of the target date in the user's current timezone
- [x] **Aspects:** 5 major aspects with per-planet orbs (§5.1)
- [x] **Moon window:** Moon aspects count if exact during the local day (00:00–24:00, DST-safe); record the local time of exactness
- [x] **Placements:** natal house of each fast transiting planet (Sun, Moon, Mercury, Venus, Mars)
- [x] **Moon sign and phase** (8 phases)
- [x] **Weighting:** transit weight × natal weight × aspect strength × orb tightness; natal Moon down-weighted when the birth time is unknown
- [x] **Slow-planet cap:** only the strongest Jupiter–Pluto factor survives, marked `background`
- [x] **Categories:** mapping by planets and houses (§5.3), smooth normalization to 1–5 paws, neutral 3 for empty categories
- [x] **Overall score and Mira's pose** (rounded average, half rounds up)
- [x] **Selection:** top 3–5 factors, always at least one Moon factor (Moon aspect, else Moon placement)
- [x] **Keyword tables** (`keywords.yaml`, our own wording): planets, natal points, aspect natures, houses, signs, category bands; deterministic seeded choice per user and date
- [x] **Settings** (`settings.yaml`): orbs, weights, tones, category mapping, normalization — all tunable without code changes
- [x] **Versioning:** `engine_version` = code version + fingerprint of the data files; `input_hash` = birth profile + engine version
- [x] **Outputs:** full engine output (stored later as `engine_json`) and the reduced LLM payload (no degrees, no orbs)

## CLI

- [x] `astrocat chart --profile <yaml>` → natal chart JSON
- [x] `astrocat day --profile <yaml> [--date YYYY-MM-DD] [--payload] [--lang en|es|de]` → engine output or LLM payload
- [x] `astrocat review --profile <yaml>… --from <date> --days <n> --engine-only [--out <html>]` → HTML report: one row per day (paws, pose, Moon, top factors), flags (Moon fallback used, empty categories), score and pose distribution

## Demo data

- [x] 3 fictional profiles in `api/demo/`: German (time known), Spanish (time known), English (time unknown)

## Tests

- [x] Reference positions (J2000)
- [x] Time conversion: summer/winter time, offset override, unknown time
- [x] Whole Sign and solar houses
- [x] Aspect detection and orbs
- [x] Moon window: the Moon is at the aspect point at the reported time
- [x] Moon phase boundaries
- [x] Determinism: same input → identical output; `input_hash` changes with birth data
- [x] Payload: no degrees/orbs; every referenced factor id exists; overall score matches the category average
- [x] Invariants over 60 days × all demo profiles: always a Moon factor, scores in 1–5, 3–5 factors
- [x] High latitude (Tromsø) works

## Tuning (with the review report)

- [x] Run 30 days for all demo profiles; adjust weights/normalization until paws use the full 1–5 range and poses vary

---

## Tuning log

- **2026-10-03, first run:** paws too extreme (1 and 5 on ~40% of days) and a constant positive bias in love. Cause: placements were mapped to categories by planet, so "Venus in any house" pushed love up every day for everyone. Fix: placements count only through their house; the background theme counts half (`background_score_share: 0.5`).
- **2026-10-03, calibration:** over 40 random charts × 20 days the raw scores had a small positive bias (+0.1, more harmonious than tense aspect types). `score_scale: 1.0`, `score_center: 0.1` → paws 1–5 ≈ 7 / 25 / 33 / 26 / 7 %. Days without any Moon aspect: ~4% (Moon placement used instead).
- **Demo profiles, 2026-10-01 + 30 days:** all five poses occur; Lucía is above average this month (her chart, not a bias).

## Observations to revisit (not blocking M1)

- On quiet days (e.g. Sam, 2026-10-03) the selection consists only of house placements. Fine for now; check in M2 whether the LLM makes good readings from that.
- A Moon placement can be selected next to a Moon aspect, which partly repeats the Moon. Possibly prefer other factors once a Moon factor is in.

## Deferred to later milestones

- City search (GeoNames `cities1000`, `timezonefinder`) → M3, with onboarding. M1 profiles contain coordinates and timezone directly.
- `weekday` / `date_label` localization → M2 (added by the API, not the engine).
- "Why Mira says this" texts in EN/ES/DE → M2/M4 (M1 has English descriptions for the review report only).
