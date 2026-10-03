# Tasks — M3: API, database, login, onboarding, scheduler ✅

Goal (see [concept.md](concept.md) §8–§11, §13): the engine and Mira's readings run as a FastAPI service in Docker, with PostgreSQL, invite-only login, onboarding data (incl. city search and form of address), on-demand readings and a background scheduler. The frontend follows in M4, so M3 is tested through the API and the CLI.

**Done when:**

- `docker compose up` starts `db` and `api`; migrations run automatically.
- An admin creates a user with `astrocat create-user`; the user logs in, completes onboarding via the API and gets today's reading from `GET /api/today`.
- The scheduler generates readings in the background without blocking requests; missed runs (Mac asleep) are caught up.
- Tests cover auth, onboarding, places, reading storage (no duplicates, recent readings from the database) and the scheduler.

---

## Setup

- [x] Dependencies: FastAPI, Uvicorn, SQLAlchemy 2, Alembic, psycopg 3, argon2-cffi, APScheduler, tzdata
- [x] Configuration from environment (`.env`, `.env.example`): database URL, Ollama, session lifetime, scheduler on/off
- [x] `compose.yaml` with `db` (PostgreSQL) and `api`; `compose.dev.yaml` publishing ports on 127.0.0.1 for development and tests
- [x] `api` Dockerfile (uv, Python 3.12); entrypoint runs migrations, then Uvicorn

## Database

- [x] Models: `users`, `birth_profiles`, `sessions`, `daily_readings`, `places`, `place_names` (concept §11)
- [x] Alembic migrations
- [x] Unique constraint on the reading cache key `(user_id, local_date, language, input_hash)`

## Auth

- [x] Password hashing with argon2
- [x] Sessions: random token in an `HttpOnly`, `SameSite=Lax` cookie, only its hash stored; ~90 days; logout deletes the session
- [x] Login rate limiting (per username and client)
- [x] CLI: `astrocat create-user`, `astrocat reset-password`
- [x] Change own password via the API

## Places (city search)

- [x] `astrocat places import`: download GeoNames `cities1000` once, load into `places` + `place_names` (alternate names, accent-insensitive)
- [x] Search endpoint: prefix match, sorted by population, returns name, country, coordinates, timezone

## Onboarding and settings

- [x] `GET /api/me` (incl. "onboarding complete")
- [x] Settings: display name, language, form of address, current timezone
- [x] Birth data: date, optional time, place (from the search), optional UTC offset override

## Readings

- [x] Reading service: get or create the reading for (user, local date, language); `generating` status; a second request waits instead of starting another LLM call; stale `generating` rows are taken over
- [x] Recent readings (last 3, same language) loaded from the database for the prompt
- [x] `GET /api/today`: reading, paw ratings, pose, Moon, factors for "Why Mira says this"
- [x] Changing birth data or the form of address produces a new reading (via `input_hash`)

## Scheduler

- [x] In-process APScheduler job every 15 minutes: for each onboarded user whose local day has started, generate today's reading if missing (catches up after sleep)
- [x] One generation at a time (Ollama runs one model), never blocking API requests

## Tests

- [x] Test database (PostgreSQL in Docker), fake LLM client
- [x] Auth: login, wrong password, rate limit, logout, session expiry, password change
- [x] Onboarding and settings validation
- [x] Places import (small fixture file) and search (accents, alternate names, population order)
- [x] Readings: created once, reused, regenerated after birth-data change, recent readings, concurrent requests → one LLM call
- [x] Scheduler: generates for users whose day started, skips others, catches up

## End-to-end check

- [x] In Docker with real Ollama: create user → login → onboarding → `GET /api/today` → reading; scheduler run in the logs

---

## M3 log

- **Stack:** FastAPI, SQLAlchemy 2 + Alembic (migrations inside the package, run on every container start), psycopg 3, argon2-cffi, APScheduler 3, PostgreSQL 17. 142 tests (38 need the dev database; they skip with a hint if it isn't running).
- **Decisions while building:**
  - **No `natal_charts` table:** computing a birth chart takes milliseconds, so caching it would only add invalidation logic.
  - **No `timezonefinder`:** GeoNames `cities1000` already contains each city's IANA timezone.
  - **City search:** `places` + `place_names` (all Latin-script alternate names, lowercase, accents removed), prefix search with a `text_pattern_ops` index, biggest city first. Import: 171,102 places, 607,528 names, ~16 s, database ~120 MB.
  - **Scheduler as a catch-up loop:** every 15 minutes it generates today's reading for every user whose local day has started (from 00:05) and who has none yet. Handles each user's timezone and a sleeping Mac with the same code.
  - **One generation at a time** (a process-wide lock), because Ollama runs one model.
  - **Duplicate protection:** `INSERT … ON CONFLICT DO NOTHING` on the reading key; other requests wait (up to 90 s, then `503` with `Retry-After`); failed rows are taken over at once, abandoned `generating` rows after 5 minutes.
  - **Sessions slide:** with less than half of the 90 days left, a request renews the session, so phones in daily use never get logged out. Only a SHA-256 of the token is stored. A password change logs out all other devices.
  - **Manual birth place** possible (name, coordinates, timezone) for places missing from the list.
  - **JSONB does not keep key order:** the API restores the category order (love, work, energy, mood) explicitly.
- **End-to-end check (Docker, real Ollama, 2026-10-03):** create user → login → search "münch" (Munich first) → form of address → birth place via search → `GET /api/today`: German reading with feminine forms, 16.4 s on the first call (incl. model load), 30 ms from the cache. Simulated scheduler run "next morning 07:40": found the missing day, generated it in 8.8 s, nothing due afterwards. Demo user deleted again; the city list stays.

## Deferred to later milestones

- Frontend (login, onboarding, Today, Settings), "Why Mira says this" texts in EN/ES/DE, `web` service with Caddy → M4.
- `astrocat review --user <username>` (review from the database) → when needed.

## M2 log (done)

- **Probe (2026-10-03):** `gemma4:e2b` (5.1B, Q4_K_M) supports `format` with a JSON schema. `think: true` triples the tokens without better text, so it stays off. ~4 s per reading, plus ~5 s model load on the first call.
- **Prompt v1, 3 × 14 days:** 42/42 valid, 0 fallbacks, 39 on the first attempt (retries only from the repetition check), median ~3.7 s. No jargon, no forbidden topics, weekdays always correct when mentioned. Quality problems:
  1. No Mira: zero cat touches; generic wellness tone ("Vertraue deinem inneren Rhythmus", "let things unfold").
  2. Abstract rather than concrete; hardly any everyday suggestions.
  3. Repetition across days, partly because the engine's category keywords (3–4 per band) were echoed literally.
  4. Spanish assumed a female reader from the name "Lucía" ("enfocada", "cómoda", "contigo misma").
  5. German slips: invented words ("Flirtungen"), old spelling ("Laß"), one broken headline.
- **Prompt v2 changes:** clever-friend voice; one concrete suggestion per section; exactly one cat touch; per-language list of clichés to avoid; gender-neutral wording rule with language-specific hints; the reader's name is no longer sent to the LLM; recent summary openings shown in the prompt and checked; category keyword bands expanded to 7–8 entries (engine version changes).
- **Prompt v2, 3 × 14 days:** 41/42 ok, 1 fallback (German summary started with "Die Stimmung ist heute" three times in a row). Much more concrete (walks, a blanket, tidying a drawer, a short message); cat touches present; weekdays used more often and always correctly. Remaining problems:
  1. The cat touch became a formula: "¡miau!" on 8 Spanish headlines in a row, "eine Katzen-Achtung" (not a word) 3× in German, "Widder-Mittwoch:"-style headline patterns.
  2. Retries repeated the rejected opening at the same temperature.
  3. Spanish still uses gendered adjectives, now randomly mixed ("valorada", "segura", but also "generoso", "satisfecho"); sometimes plural address ("compartís", "Disfrutad").
  4. German is the weakest language: "die Momentum", "Charm", "Dranghaftigkeit", "Decke-Moment".
- **Prompt v3 changes:** headline check rejects the same first content word or last word as a recent headline; cat touch must vary, no tagged-on "meow", no "kitty"; singular address only (Spanish: never "vosotros"); Spanish check for gendered adjectives after "sentir"/"estar" etc.; temperature rises with each retry (0.7 → 0.85 → 1.0). German additionally compared with `gemma4:e4b`.
- **Prompt v3, 3 × 14 days:**
  - `e2b` English: 14/14, median 3.8 s, good quality.
  - `e2b` Spanish: 13/14, but only 5 on the first attempt, median 7.7 s. The gender check catches a lot ("segura", "valorada", "ti misma"), but the model keeps producing gendered adjectives; one fallback after three rejections. Cat touch repeats ("¡qué gato!").
  - `e2b` German: 13/14, 1 fallback (same summary opening and headline pattern again); grammar slips continue.
  - `e4b` German: 14/14, 13 on the first attempt, median 9.8 s (max 17 s). Clearly more concrete and natural ("zieh dir deine weichsten Socken an", "frag gezielt nach einem Beispiel"), varied cat touches ("Schnurr-Tipp", "Fell-Nickerchen"). Still occasional grammar slips ("du fallen mit") and one invented word ("Fellknicknagel").
  - Bug found: the sentence splitter treated "z.B." as a sentence end, so trimming cut a German section mid-sentence. Fixed (abbreviation list, split only before an uppercase letter).
- **v4 changes:** Spanish gender check allows up to 3 words between verb and adjective ("te sientes muy alegre y generosa"); no nicknames for the reader ("kitty", "my cat", "friend"). Testing `e4b` for all languages: with readings pre-generated at night, ~10 s per reading is acceptable, and one model avoids swapping between models.
- **v4 with `gemma4:e4b`, 3 × 14 days:** 42/42 ok, 0 fallbacks; first attempt DE 13, ES 9, EN 12; median 6.5–8.5 s, max 22 s. Best quality so far in all three languages: concrete ("ask a colleague about a process you haven't quite grasped", "frag spezifisch nach dem ersten Schritt"), varied cat touches ("Don't get tangled in the yarn", "hasta el bigote", "Fellknäuel an Ruhe"), weekdays always correct, no jargon. Cross-language run (Anna in English, 7 days): 7/7 on the first attempt.
- **Decision:** `gemma4:e4b` is the default for all languages (`OLLAMA_MODEL` still overrides). `e2b` is fine for English but not good enough for Spanish and German.
- **Known residuals (accepted for now):**
  - Spanish with `neutral`: the model still slips into the generic masculine now and then; resolved for users who pick a form (see the setting below).
  - Favorite images repeat across days ("flotter Spaziergang" 6×, "maullido" 5×).
  - Occasional small German slips ("auch wenn es dir kostet", "Samstag's") and a nickname despite the rule ("kleine Maus").
  - Spanish occasionally slips into plural address ("os", "comáis") when talking about the reader and someone else.
- **Grammatical gender as a per-user setting (decided 2026-10-03):** profile field `grammatical_gender` (`neutral` default, `feminine`, `masculine`), part of `input_hash`, passed in the payload. Per-language prompt hints for each value; the check rejects only the wrong forms (neutral: any gendered adjective). Lucía set to `feminine`: 14/14 ok, consistently feminine forms ("cómoda contigo misma", "agradecida"), zero gender rejections (v4: 3–5 per 14 days).
- **Fix after v4:** English headlines lowercased weekdays ("for saturday") → sentence-case rule now keeps proper nouns capitalized.

## M1 tuning log (done)

- **2026-10-03, first run:** paws too extreme (1 and 5 on ~40% of days) and a constant positive bias in love. Cause: placements were mapped to categories by planet, so "Venus in any house" pushed love up every day for everyone. Fix: placements count only through their house; the background theme counts half (`background_score_share: 0.5`).
- **2026-10-03, calibration:** over 40 random charts × 20 days the raw scores had a small positive bias (+0.1, more harmonious than tense aspect types). `score_scale: 1.0`, `score_center: 0.1` → paws 1–5 ≈ 7 / 25 / 33 / 26 / 7 %. Days without any Moon aspect: ~4% (Moon placement used instead).
- **Demo profiles, 2026-10-01 + 30 days:** all five poses occur; Lucía is above average this month (her chart, not a bias).

