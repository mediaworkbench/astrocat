# AstroCat — Concept

> Status: MVP concept, v6 (2026-10-03) — all five milestones are built: engine, LLM, API/database/scheduler, app, and Mira with her moods; this version includes what we learned there. Progress and tuning logs: [TASKS.md](TASKS.md).

**AstroCat** is a mobile-first daily horoscope PWA. Mira, a charming cat guide, presents each user's personal daily reading, calculated from their own birth chart and today's planetary transits. A deterministic astrology engine decides *what* the day looks like; a local LLM only decides *how to say it* — in Mira's voice, in English, Spanish, or German.

#### Taglines

- "Your daily stars, delivered by a cat."
- "Daily horoscopes with a little more magic."

![AstroCat key visual](artwork/astrocat.png)

---

## 1. Context and goals

#### Context

- Personal project, completely free, no monetization.
- Runs on a Mac at home; used by **3 users** on their phones via the **home Wi-Fi only**.
- May be published as an open-source project on GitHub later.

#### MVP goals

- Each user gets one personal reading per day, based on their birth data.
- Readings are available in **English, Spanish, and German** (per-user setting).
- Opening the app is instant (reading is pre-generated or cached).
- The cat feels like a real character with a consistent voice and visible moods.
- The astrology logic is deterministic and testable, independent of the LLM.

#### Non-goals for the MVP

- Push notifications, offline mode, HTTPS
- Open sign-up or hosting outside the home network (self-registration needs an invite code, §9)
- Compatibility between users, weekly/monthly horoscopes, share cards
- Native apps

---

## 2. Product experience

#### Feel

- Cute but not childish; modern, clean, premium.
- Celestial visuals: stars, moons, soft gradients, subtle glow; a Moon phase icon for today's Moon, an occasional shooting star, and sections that appear one after another.
- The cat is a knowledgeable companion, not just a mascot.
- Personal, fun, and lightly magical rather than serious.

#### Layout

- Portrait, single column, designed for one-handed use. Mira sits at the top of the Today screen; content flows below. The headline and the start of the summary are visible without scrolling.
- Dark night-sky theme only: the app is about the night sky, and a light theme is not planned.
- The key visual above is landscape and has text baked in. For the app we need portrait-friendly art **without text in images** (titles and labels are real text, so they can be translated and are accessible).

#### Screens

| Screen | Content |
|---|---|
| Login | Username + password. "Create account" link only when an invite code is configured. |
| Create account | Username, password, invite code; language and timezone from the browser. Logs in and continues with onboarding. |
| Onboarding | Display name, language, how Mira should address you (feminine / masculine / neutral forms; matters for Spanish and German), birth date, birth time (optional, "I don't know" checkbox), birth place (city search), current timezone (prefilled from the browser). |
| Today | Day switch "Today · Tomorrow · Day after tomorrow" at the top · Mira in the day's pose · headline · short summary · category cards with paw ratings · Mira's advice · expandable "Why Mira says this". |
| Settings | Language, form of address, birth data, timezone, change password, logout, "Source code" link (§12). |

**Loading state:** if a reading is not ready yet, Mira is shown "reading the stars" (small animation) while it is generated on demand.

---

## 3. Mira, the cat

**Name:** Mira — a real star (Mira, in Cetus), easy to say in all three languages, and Spanish *"¡Mira!"* ("Look!") fits a cat holding up your horoscope card.

#### Personality

- Curious, warm, confident, a little sassy.
- Wise but never preachy; encouraging even on difficult days.
- Speaks directly to the user ("you"), informal register: *du* in German, *tú* in Spanish.
- Uses the grammatical gender the user chose (feminine / masculine); with "neutral" it rephrases instead of using gendered adjectives. The user's name is never sent to the LLM, so it cannot guess a gender from it.

#### Voice rules

- Writes like a clever friend with a sense of humor, **not like a wellness app**.
- Short sentences. **Every section contains one concrete, everyday suggestion** (send a short message, take a walk, tidy one drawer, cook something warm, go to bed early).
- **Exactly one light cat touch per reading** (a pun or a cat image, preferably in the headline or the advice), different every day. Never a tagged-on "meow", never a nickname for the reader ("kitty", "my cat", "friend").
- Avoids overused phrases; each language has its own list (e.g. "embrace", "let things unfold", "Vertraue", "innerer Rhythmus", "fluir", "permítete").
- Addresses only the reader, in the singular (Spanish: never *vosotros*).
- Difficult days are framed as "be gentle / take your time", never as doom.
- **No jargon in the prose.** Planet and sign names are fine ("the Moon", "Venus", "Pisces"); aspect names, houses, orbs and terms like "natal" or "transit" are not. Technical detail lives only in the "Why Mira says this" section.
- **Refer to the day by its weekday** ("this Saturday"), using the date label from the payload — never work it out from the date.

#### Mira never

- predicts accidents, illness, death, or catastrophes
- gives medical, financial, or legal advice
- tells the user to end or start a relationship
- guilts or shames the user

**Example lines** (reference for the prompt; one per language)
- EN: "The Moon is purring in your favor today — say the kind thing you've been holding back."
- ES: "Hoy la Luna ronronea a tu favor: di eso amable que te has estado guardando."
- DE: "Der Mond schnurrt heute auf deiner Seite – sag das Nette, das du dir bisher verkniffen hast."

**Poses (visual)** — the engine's overall day score selects Mira's pose. Each pose has its own illustration (sources in `artwork/`) plus light and motion in the app:

| Score | Pose | Illustration | In the app |
|---|---|---|---|
| 1 | sleepy | curled up on a cloud, winking with one eye, card beside her | cool, dim light; slow sway; "z z z" rising above her head |
| 2 | cautious | sitting, worried look, hugging the card, tail wrapped | muted light, gentle breathing |
| 3 | calm | sitting cross-legged, meditating with closed eyes, sparkles around her | warm glow, gentle breathing |
| 4 | playful | on hind legs, reaching for a glowing star, card in the other paw | brighter glow, little hops |
| 5 | radiant | card held high, eyes closed with joy, sparkles | strong pulsing glow, floating |

Login and onboarding show the standing Mira from `artwork/standing.png`, holding up her card. While a reading is generated, she "reads the stars": a golden halo pulses behind her card and two stars circle slowly.

**Assets:**
- **Sources** in `artwork/`: `standing.png` and the five poses `sleepy.png`, `cautious.png`, `calm.png`, `playful.png`, `radiant.png` (single illustrations, 2026-10-06), all in one style: crisp outlines, a dark card with golden lines, no glow halo. `mira-character.png` is the first character art; the app icons still come from it. No text in images (§2).
- **App files:** `web/src/assets/mira.webp` (standing Mira, from `standing.png`) and `web/src/assets/poses/<pose>.webp`. A pose image replaces the standing Mira for that pose automatically; without one, the app falls back to the standing Mira with generated effects (dimming, clouds, an orbiting star, sparkles).
- **Resolution:** the poses are exported at 900 px height (sleepy, which is wide: 1000 px width), sharp on 3× phone screens, 110–205 KB each (the standing Mira likewise).
- **Motion:** CSS only (no Rive or Lottie needed); all animation stops with the system setting "reduce motion".

---

## 4. Daily reading content

Each reading contains:

| Part | Source | Length |
|---|---|---|
| Headline | LLM | max ~60 characters |
| Summary | LLM | 2–3 sentences |
| Love, Work, Energy, Mood | text: LLM · paw rating (1–5): engine | 1–2 sentences each |
| Mira's advice | LLM | 1 sentence |
| "Why Mira says this" | engine + i18n templates in the app (no LLM) | list of today's top factors, e.g. "Venus trine your Moon · supportive · 5th house: romance, play and creativity" |
| Disclaimer | static i18n text | "For entertainment." |

"Health" from v1 is renamed **Energy** to avoid medical territory.

**Unknown birth time:** readings still work (see §5.2); the "Why" section shows a small hint that house-based details are approximate.

---

## 5. Astrology engine

The engine is pure Python, deterministic, and has no knowledge of the LLM. Given birth data and a date, it always produces the same JSON.

### 5.1 Settings (defaults)

| Setting | Value |
|---|---|
| Zodiac | Western, tropical |
| House system | Whole Sign (simple, robust at all latitudes) |
| Bodies | Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto; Ascendant only if birth time is known |
| Aspects | conjunction, sextile, square, trine, opposition |
| Transit orbs | Sun/Mercury/Venus/Mars 2°, Jupiter/Saturn 1.5°, Uranus/Neptune/Pluto 1°. The Moon has no orb: its aspects count when they become exact during the local day (§5.3). |
| Ephemeris | `libephemeris`, network access disabled ("sealed"): no downloads at runtime |

All values live in `api/src/astrocat/engine/data/settings.yaml`. Any change there (or in `keywords.yaml`) changes the engine version fingerprint, so cached readings are regenerated automatically.

### 5.2 Inputs

- **Birth date and local clock time.** Converted to UTC with `zoneinfo` using the historical timezone of the birth place. An optional manual UTC offset override covers cases where historical tz data is wrong (mostly births before ~1970 in some regions).
- **Birth time unknown → noon fallback.** The chart is cast for 12:00 local time, there is no Ascendant, and houses fall back to **solar houses** (Whole Sign counted from the Sun sign). Aspects to the natal Moon get a lower weight, since its position is uncertain by up to ~7°.
- **Birth place.** Offline city search using the GeoNames `cities1000` dataset (`cities15000` would miss many small birth towns), matching alternate names too (Munich / München / Múnich), accent-insensitive, biggest city first. GeoNames already contains each city's IANA timezone, so no extra library is needed. The list is downloaded once by an admin command (`astrocat places import`); at runtime there is no external API (privacy, offline-friendly). Places missing from the list can be entered manually (name, coordinates, timezone). GeoNames is CC BY 4.0 → attribution required.
- **Today.** The transit chart is computed for **local noon of the target date** in the user's *current* timezone.

### 5.3 Daily computation

1. **Natal chart:** computed once per user and cached; recomputed only when birth data or the engine version changes.
2. **Transit chart** for the target date (local noon).
3. **Factors:** all transit-to-natal aspects within orb, plus the natal house each transiting planet is in, plus the Moon's sign and phase.
   - **Moon exception:** the Moon moves ~13° per day, so a noon snapshot misses many of its aspects. Moon aspects count if they become exact at any time during the local day (00:00–24:00).
4. **Weighting:** `weight = transit-planet weight × natal-point weight × aspect strength × orb tightness`. Placements ("Venus in your 5th house") count for the fast planets (Sun–Mars, Moon) with a low weight.
   - The Moon gets a high weight — it moves ~13°/day and provides the day-to-day variety.
   - Slow planets (Jupiter–Pluto) are capped to **one background theme**, otherwise the same transit would dominate for weeks.
5. **Categories:** each aspect contributes to one or more categories via its planets and houses; a placement ("Venus in your 5th house") only via its house, otherwise e.g. Venus would push every love score up every day (starting mapping, to be tuned):

   | Category | Planets | Houses |
   |---|---|---|
   | Love | Venus, Moon | 5, 7 |
   | Work | Sun, Mercury, Saturn, Jupiter | 6, 10 |
   | Energy | Mars, Sun | 1, 6 |
   | Mood | Moon, Neptune | 4, 12 |

   Harmonious aspects (trine, sextile) raise a score, tense ones (square, opposition) lower it, and conjunctions follow the planet's nature. The background theme counts half. Each category is normalized to **1–5 paws** with a smooth curve, `3 + 2·tanh((raw − 0.1) / 1.0)`, calibrated in M1 on 40 random charts: 1–5 paws ≈ 7 / 25 / 33 / 26 / 7 %. The 0.1 offsets a small built-in positive bias (more aspect types count as harmonious than as tense). The overall day score (→ Mira's pose) is the average of the four categories, rounded half up.
6. **Selection:** the top 3–5 factors are passed on, always including at least one Moon factor. If the Moon makes no aspect that day, the Moon's natal house serves as the Moon factor (it always exists).
7. **Empty categories:** a category without any factor gets a neutral score of 3 and keywords from the Moon's sign and house.

### 5.4 Interpretation keywords

Instead of writing a text for every planet × aspect × planet × category combination (hundreds of texts), the engine uses small **keyword tables**:
- per planet (e.g. Venus → affection, beauty, pleasure)
- per aspect nature (harmonious → ease, flow; tense → friction, growth through effort)
- per house (5 → romance, play, creativity)
- per sign (for the Moon's daily sign)
- per category and score band (low / mid / high), 7–8 entries each, so consecutive days rarely get the same hints (M2: with 3–4 entries the LLM echoed the same phrases every day)

Keywords are chosen with a random generator seeded by user and date, so the output stays deterministic. The engine selects keywords; the LLM combines them into prose. The tables live as versioned YAML files in the repo, in English, and are written by us (no copying from books or websites — important for the open-source release).

---

## 6. LLM layer

- **Runtime:** Ollama on the macOS host (outside Docker), reached from containers at `http://host.docker.internal:11434`. `OLLAMA_BASE_URL` in `.env` points it elsewhere, e.g. to a stronger computer in the network.
- **Model:** `gemma4:e4b` (chosen in M2: `e2b` is fine for English but too weak in Spanish and German; `e4b` takes ~8 s per reading); base URL and model name are configurable via `.env`.
- **Role:** turns the engine JSON into prose. It never sees raw positions or degrees, and it never decides ratings or poses.
- **Thinking mode off:** `think: true` roughly triples the tokens without better readings (M2 probe).
- **Language packs:** one YAML file per language (`api/src/astrocat/llm/data/{en,es,de}.yaml`) with localized planet/sign/phase/weekday/month names, the style example, the cliché list, gender hints, check patterns, and the fallback texts. The system prompt is `system_prompt.txt`. Any change to these files changes the prompt version.

#### Prompt structure

- **System prompt:** Mira's persona and voice rules (§3), content rules, length limits, the target language and register (*du* / *tú*, singular), the cliché list and the gender hint for the user's setting, plus one full style example in that language ("copy the style, never the sentences").
- **User message — a short brief, not raw JSON:** the LLM payload (§7.1) rendered as a few lines of text. Planet, sign, Moon-phase and weekday names are **already localized**, so the model never translates astrology terms itself; keywords stay in English as hints. The user's **name is left out**: in M2 the model guessed a gender from "Lucía".
- **Recent readings block:** the headlines, advice and summary openings of the user's last 3 readings in the same language, with the instruction not to reuse them. Small models repeat themselves easily. (This comes from the database, not from the engine, so the engine stays deterministic.)

#### Output control

- Structured output via Ollama's `format` parameter with the JSON schema from §7.2.
- **Repair before validation:** surplus sentences are trimmed instead of rejecting the reading (the sentence splitter ignores dates like "3. Oktober" and abbreviations like "z.B.").
- **Validation:**
  - schema and length limits
  - forbidden topics and astrology jargon (per-language patterns, e.g. trine / trígono / Trigon, "5. Haus")
  - language check (the reading must be in the requested language)
  - wrong weekday (any weekday other than today's)
  - grammatical gender: rejects forms that don't match the user's setting (§3)
  - repetition against the last 3 readings: similar headline or advice, same summary opening, or a headline that starts or ends with the same word (catches formulas like "…, ¡miau!" or "Widder-Mittwoch:")
- **Retries:** up to 2, with the rejection reasons fed back to the model and a **rising temperature** (0.7 → 0.85 → 1.0); at the same temperature the model tends to repeat a rejected phrase.
- **Fallback:** after 3 failed attempts, or immediately if Ollama is unreachable, a **template reading** from the language pack: sentences per category × score (60 per language) plus headline, summary and advice per overall score. The keyword tables are English-only, so they can't be used for Spanish or German fallback text.
- Every stored reading records status, attempts, rejection reasons, model, prompt version, engine version and duration.

#### Glossary example

Planet, sign and phase names come from the language packs and are used both in the brief and later in the "Why" section. The aspect and house terms below are only for the "Why" i18n templates (M4); the LLM must not use them (§3).

| EN | ES | DE |
|---|---|---|
| Libra | Libra | Waage |
| trine | trígono | Trigon |
| square | cuadratura | Quadrat |
| natal Moon | Luna natal | Geburtsmond |
| house | casa | Haus |

#### Review tool

A CLI command renders a series of days as one HTML page for tuning and quality checks, e.g. `astrocat review --profile demo/anna.yaml --from 2026-10-01 --days 14 [--lang de] [--model gemma4:e2b]`. It reads birth data from a YAML file because the database only arrives in M3 (`--user <username>` can be added then). Days are generated in order, so the recent-readings block (above) is exercised too:

- one row per day: paw ratings, Mira's pose, top factors (engine) next to the generated reading (LLM)
- flags: rejected attempts with reasons, fallback readings, repeated summary openings across days
- LLM summary: valid/fallback counts, first-attempt rate, median and max duration
- summary: distribution of scores and poses over the period (are the paws actually varied, or stuck at 3?)
- `--engine-only` skips the LLM for fast tuning of weights and orbs

#### M2 outcome

Four prompt rounds, each reviewed on 3 profiles × 14 days. Final round with `gemma4:e4b`: 42/42 valid, no fallbacks, median 6.5–8.5 s, concrete and varied readings in all three languages. `gemma4:e2b` was fine in English but made too many mistakes in Spanish and German. Known weaknesses: favorite images repeat across days ("flotter Spaziergang"), and German has occasional small grammar slips. Details per round: [TASKS.md](TASKS.md).

---

## 7. JSON contract

### 7.1 Engine → LLM

The engine produces a full output (positions, degrees, orbs, all factors), which is stored as `engine_json` and feeds the "Why" section. The LLM receives only a **reduced payload** without any degrees or orbs:

```json
{
  "contract_version": 1,
  "date": "2026-10-03",
  "weekday": "saturday",
  "date_label": "Samstag, 3. Oktober",
  "language": "de",
  "user": {
    "display_name": "Anna",
    "sun_sign": "libra",
    "birth_time_known": true,
    "grammatical_gender": "feminine"
  },
  "day": {
    "moon_sign": "pisces",
    "moon_phase": "waxing_gibbous",
    "overall_score": 4,
    "mira_pose": "playful"
  },
  "categories": {
    "love":   { "score": 5, "keywords": ["warmth", "easy connection"], "factor_ids": ["f1"] },
    "work":   { "score": 2, "keywords": ["friction", "patience with structures"], "factor_ids": ["f2"] },
    "energy": { "score": 4, "keywords": ["drive", "momentum"], "factor_ids": ["f3"] },
    "mood":   { "score": 4, "keywords": ["dreamy", "intuitive"], "factor_ids": ["f1", "f4"] }
  },
  "factors": [
    {
      "id": "f1",
      "transit": "venus", "aspect": "trine", "natal": "moon",
      "house": 5, "nature": "harmonious",
      "keywords": ["affection", "emotional ease", "romance"]
    },
    {
      "id": "f2",
      "transit": "saturn", "aspect": "square", "natal": "sun",
      "house": 10, "nature": "tense", "background": true,
      "keywords": ["responsibility", "slow progress", "structure"]
    },
    {
      "id": "f3",
      "transit": "mars", "aspect": "sextile", "natal": "sun",
      "house": 1, "nature": "harmonious",
      "keywords": ["initiative", "physical energy"]
    },
    {
      "id": "f4",
      "transit": "moon", "aspect": "conjunction", "natal": "neptune",
      "house": 12, "nature": "neutral",
      "keywords": ["imagination", "need for quiet"]
    }
  ]
}
```

### 7.2 LLM → API

```json
{
  "headline": "string, max 60 chars",
  "summary": "string, 2–3 sentences",
  "sections": {
    "love": "string, 1–2 sentences",
    "work": "string, 1–2 sentences",
    "energy": "string, 1–2 sentences",
    "mood": "string, 1–2 sentences"
  },
  "advice": "string, 1 sentence"
}
```

Scores, Mira's pose, and the "Why" list come from the engine output, not from the LLM. `house` is the natal house the transiting planet is in. The overall score 4 is the rounded average of the category scores (3.75). `weekday` and `date_label` are added by the API (localized with the tables in the language packs, no extra dependency), because small models often get the weekday of a date wrong; the engine itself stays language-independent. `display_name` stays in the payload for the app, but is not passed on to the model (§6).

---

## 8. Generation and caching

- **Cache key:** `(user_id, local_date, language, input_hash)`, where `input_hash` hashes the birth profile, the form of address, and `engine_version`. Editing birth data or the form of address therefore produces a new reading automatically, without separate invalidation logic. Each reading also stores `engine_version`, `prompt_version`, and the model name.
- **Scheduled job as a catch-up loop:** every 15 minutes, the job generates the missing readings for every user whose local day has started (from 00:05 local time): first today for everyone, then tomorrow and the day after (`GENERATE_DAYS_AHEAD`, default 2), so the app's day switch is instant. After the first run only one new day per user and day is added. Generating in date order also gives each prompt its predecessors for the recent-readings block. The same code handles each user's timezone and a Mac that slept through the night. With 3 users this is 3 LLM calls per day. Only one reading is generated at a time, since Ollama runs one model.
- **On demand:** if a reading is missing (e.g. the Mac was asleep), it is generated when the user opens the app; Mira's loading animation covers the wait (with `gemma4:e4b` typically ~8 s, up to ~20 s when retries are needed; plus a few seconds if Ollama first has to load the model).
- **No duplicates:** a unique constraint on the cache key plus a `generating` status. If two requests arrive at once, the second one waits for the first instead of starting another LLM call (up to 90 s, then `503` with `Retry-After`, and the app retries). A failed generation is retried by the next request; a `generating` row abandoned by a crash is taken over after 5 minutes.
- **Outages heal themselves:** a template reading caused by Ollama being unreachable is marked and regenerated by the next scheduler run once Ollama answers again. Template readings caused by the model failing the checks are kept (it already had its 3 attempts).
- **History:** past readings stay in the database (enables a history view later at no extra cost).

---

## 9. Users and authentication

- **Invite-only:** accounts come either from self-registration in the app with an **invite code**, or from the admin command `docker compose exec api astrocat create-user <username>`.
  - The code is `REGISTRATION_CODE` in `.env`; empty = registration off (the app hides the link). Change it to stop further sign-ups; existing accounts are not affected.
  - The code is compared in constant time; wrong codes share the login rate limit (5 per 15 minutes, then `429`).
  - Usernames: 3–32 characters, lowercase letters, digits, dot, underscore, hyphen (same rule for the CLI).
- Username + password; passwords hashed with **argon2**.
- Server-side sessions in Postgres, sent as an `HttpOnly`, `SameSite=Lax` cookie. Only a SHA-256 of the random token is stored. Sessions last 90 days and slide: with less than half the time left, any request renews them, so phones in daily use stay logged in.
- Users can change their own password in Settings (this logs out their other devices); a forgotten password is reset with `astrocat reset-password <username>`.
- Login rate limiting: 5 failed attempts per username within 15 minutes, then `429` with `Retry-After` (in memory; resets when the api restarts).
- **iOS:** a home-screen app has its own cookie storage, separate from Safari. Users log in once *inside* the installed app.
- Because the MVP runs on plain HTTP in the home network, the cookie cannot use the `Secure` flag. This is acceptable on a trusted home Wi-Fi and is documented; it changes once HTTPS is added.

---

## 10. Architecture

```text
 Phone (browser / home-screen app)
            │  http://<mac-ip>
            ▼
 ┌──────────────────── Docker on the Mac ────────────────────┐
 │  web  (Caddy)  ── static PWA build                        │
 │        │  /api/*                                          │
 │        ▼                                                  │
 │  api  (FastAPI: auth, engine, LLM client, scheduler) ──► db (PostgreSQL)
 └────────┬──────────────────────────────────────────────────┘
          │ host.docker.internal:11434
          ▼
   Ollama on macOS (gemma4:e4b)
```

| Service | Contents |
|---|---|
| `web` | Caddy serving the static frontend build and reverse-proxying `/api` to `api`. Single entry point, port 80 (`WEB_PORT`). |
| `api` | FastAPI app containing the astrology engine (`libephemeris`), LLM client, auth, and an in-process scheduler (APScheduler). |
| `db` | PostgreSQL: users, sessions, natal charts, daily readings. |
| Ollama | Runs natively on macOS, not in Docker. |

**Frontend:** Vite + React + TypeScript, with `react-i18next` for UI strings in EN/ES/DE (before login from the browser language, after login from the profile). Fonts are bundled, so the app makes no requests to external services. Next.js is not needed: there is no server-side rendering requirement, and FastAPI already owns the backend. A Playwright script (`web/scripts/screenshots.mjs`) walks through the app at phone size in WebKit and Chromium for visual checks.

**Dropped from v1:** separate `ephemeris` service (it's a library inside `api`), Redis (Postgres + in-process scheduler are enough at this scale).

**Files:** `compose.yaml` (`web`, `api`, `db`), `compose.dev.yaml` (adds ports on 127.0.0.1 for development and tests: db 55432, api 8000), `.env` (from `.env.example`; database password, Ollama model, session and scheduler settings). The `api` container runs `astrocat migrate` on every start, then `astrocat serve`.

### 10.1 API

All routes live under `/api` (OpenAPI docs at `/api/docs`). Everything except `health`, `auth/login` and the two registration routes requires a session.

| Route | Purpose |
|---|---|
| `GET /api/health` | Liveness and database check |
| `POST /api/auth/login`, `POST /api/auth/logout` | Session cookie |
| `GET /api/auth/registration` | Whether "Create account" is offered |
| `POST /api/auth/register` | Create an account with the invite code; logs in (`403` wrong code, `404` registration off, `409` username taken) |
| `GET /api/me` | Profile, settings, birth data, `onboarding_complete` |
| `PUT /api/me/settings` | Display name, language, form of address, current timezone |
| `PUT /api/me/birth` | Birth date, optional time, place (`place_id` from the search, or a manual place), optional UTC offset override |
| `POST /api/me/password` | Change password |
| `GET /api/places?q=` | City search (onboarding) |
| `GET /api/reading?offset=0\|1\|2` | The reading for today, tomorrow or the day after (in the user's timezone); same content as `/api/today` |
| `GET /api/today` | Today's reading: texts, paw ratings, pose, Moon, factors for "Why Mira says this"; `409` without birth data, `503` while another request generates it |

Admin commands run inside the container, e.g. `docker compose exec api astrocat create-user anna`: `create-user`, `reset-password`, `places import`, `migrate`.

### 10.2 Home network setup

- Give the Mac a **fixed LAN IP** (DHCP reservation in the router).
- Expose only `web` on port 80 (or 8080) to the LAN; allow it in the macOS firewall. `api` and `db` publish no ports and are reachable only inside the Docker network.
- The Mac must be awake for the app to be reachable. On-demand generation (§8) covers readings missed while it slept.

### 10.3 PWA without HTTPS

- The MVP runs over **plain HTTP** on the home network.
- Web app manifest + icons so users can add AstroCat to their home screen. iOS should open it in standalone mode (verify early in M4); on Android without HTTPS it behaves like a home-screen shortcut.
- No service worker in the MVP (browsers require HTTPS for it). Offline mode and push are out of scope anyway.
- **When HTTPS is needed later** (push, offline), without Tailscale:
  - **Caddy local CA:** Caddy issues certificates from its own CA; install and trust the root certificate once on each phone.
  - **Free DuckDNS subdomain + Let's Encrypt DNS-01** via Caddy: the subdomain points to the Mac's LAN IP. Some routers block DNS answers with private IPs (DNS rebinding protection) and need an exception for that domain.

---

## 11. Data model (sketch)

| Table | Key fields |
|---|---|
| `users` | id, username, password_hash, display_name, language, grammatical_gender (neutral / feminine / masculine), timezone, created_at |
| `birth_profiles` | user_id, birth_date, birth_time (nullable), place_name, latitude, longitude, birth_timezone, utc_offset_override (nullable) |
| `daily_readings` | user_id, local_date, language, input_hash, engine_json, reading_json, status (generating / ok / fallback / failed), attempts, rejection reasons, model, prompt_version, engine_version, duration, created_at |
| `sessions` | id (SHA-256 of the cookie token), user_id, created_at, expires_at |
| `places` | GeoNames id, name, country code, latitude, longitude, timezone, population |
| `place_names` | place_id, normalized name (lowercase, no accents; one row per alternate name) |

No table for natal charts: computing a birth chart takes milliseconds, so caching it would only add invalidation logic.

---

## 12. Open-source readiness

- All configuration and secrets in `.env`, with a `.env.example` in the repo.
- Birth data never leaves the local machine; no telemetry, no external APIs at runtime (the city list is downloaded once by an admin command).
- Interpretation keywords and texts are our own.
- Seed/demo data uses fictional people only.
- Attribution for GeoNames (CC BY 4.0).
- **License: AGPL-3.0.** `libephemeris` is AGPL-3.0-only (checked 2026-10-03, v3.2.1), so AstroCat is released under AGPL-3.0 too. Because the app is used over a network, the AGPL requires offering its source to users: the settings screen links to <https://github.com/mediaworkbench/astrocat> (`SOURCE_URL`). The license text is in `LICENSE`.

---

## 13. Milestones

The riskiest parts (engine plausibility, LLM quality in 3 languages) come first.

| # | Milestone | Done when | Status |
|---|---|---|---|
| M1 | Engine as CLI | Birth data + date → engine JSON (§7.1); unit tests with known charts; noon fallback works; `review --engine-only` shows varied scores over 30 days. | ✅ done |
| M2 | LLM spike | Engine JSON → reading in EN/ES/DE; validation, retries, template fallback; a 14-day review (review tool, §6) per language passes a manual quality check: no jargon, correct weekdays, no obvious repetition. | ✅ done |
| M3 | API + DB + auth | Login, onboarding (incl. city search and form of address), `GET /api/today`, scheduler, admin `create-user`; readings stored with recent-reading lookup from the database. | ✅ done |
| M4 | Frontend | Login, onboarding, Today, Settings; mobile layout; i18n incl. "Why Mira says this" texts; manifest; `web` service (Caddy). | ✅ done |
| M5 | Polish | Mira from the character art, five pose illustrations, loading animation, Moon phase icon, celestial styling. | ✅ done |

---

## 14. Later

- HTTPS (§10.3), then push notifications ("Mira has your reading 🐾") and offline mode.
- History view of past readings.
- Lucky color / number of the day.
- Shareable story cards (9:16).
- Weekly overview.
- Compatibility between users.

---

## 15. Open questions

- Final orbs, weights, and category mapping: calibrated in M1 on random charts; re-check with the 3 real users' charts once they are in the database.
- Repeated favorite images across days (e.g. "flotter Spaziergang"): possibly pass recent suggestions to the prompt, or accept.
- Mira's art: higher-resolution exports (≥ 1000 px per cat) of the character and pose images.
- On quiet days the selection may consist only of house placements, and a Moon placement can be selected next to a Moon aspect (M1 observations). Readings were fine in M2; revisit only if users notice.

---

## References

- libephemeris — <https://github.com/g-battaglia/libephemeris> · <https://pypi.org/project/libephemeris/>
- GeoNames — <https://www.geonames.org/>
