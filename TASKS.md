# Tasks — M2: LLM spike ✅

Goal (see [concept.md](concept.md) §3, §6, §7, §13): engine payload → Mira's reading in EN/ES/DE via local Ollama (`gemma4:e2b`), with validation, retries and a template fallback, checked with the review tool.

**Done when:**

- `astrocat reading` produces a validated reading (or a fallback) for any profile, date and language.
- `astrocat review` (with LLM) renders 14 days per language next to the engine data, with flags.
- A 14-day review per language passes a manual quality check: no jargon, correct weekdays, no obvious repetition, Mira's voice, correct register (*du* / *tú*).

---

## Setup

- [x] Probe `gemma4:e2b` in Ollama: structured output (`format` with JSON schema), thinking mode, latency
- [x] Configuration via environment: `OLLAMA_BASE_URL` (default `http://localhost:11434`; in Docker later `http://host.docker.internal:11434`), `OLLAMA_MODEL` (default `gemma4:e2b`), timeout
- [x] HTTP client dependency (`httpx`, also needed by FastAPI in M3)

## Prompt

- [x] System prompt: Mira's persona, voice rules, "Mira never" rules, no-jargon rule, weekday rule, output length limits (§3)
- [x] Language blocks (EN/ES/DE): language name, register, glossary of planet and sign names, 1–2 example readings
- [x] User message: LLM payload + localized `weekday` / `date_label` (own tables for 3 languages, no extra dependency)
- [x] Recent readings block: last 3 headlines + advice, "do not reuse these phrases or openings"
- [x] `PROMPT_VERSION`, stored with every reading

## Generation

- [x] Output JSON schema (§7.2), passed to Ollama's `format`
- [x] Temperature ~0.7
- [x] **Validation:** schema, length limits, forbidden topics, language check, jargon check, repetition check, wrong-weekday check
- [x] **Retries:** up to 2, with the validation errors fed back into the retry
- [x] **Template fallback:** per category × score × language (60 sentences) plus headline/summary/advice per pose × language
- [x] Result record: reading, status (`ok` / `fallback`), attempts, validation errors, model, prompt version, engine version, duration
- [x] Ollama unreachable → fallback immediately (no crash)

## CLI

- [x] `astrocat reading --profile <yaml> [--date] [--lang]` → reading JSON
- [x] `astrocat review` without `--engine-only`: days generated in order (recent-readings block exercised), reading text next to engine data, flags for retries/fallbacks/validation errors, timing summary

## Tests (no Ollama needed)

- [x] Date labels for all 3 languages
- [x] Validators: each check catches a bad example and passes a good one
- [x] Fallback covers every category × score × language and every pose × language, and passes validation
- [x] Generation flow with a fake client: ok on first try, retry then ok, all invalid → fallback, unreachable → fallback
- [x] Prompt contains glossary, examples, recent readings, date label; never degrees or orbs

## Quality check

- [x] 14-day review per language (Anna/DE, Lucía/ES, Sam/EN, plus one cross-language run)
- [x] Record findings and prompt changes in the log below; decide whether `gemma4:e2b` is good enough per language (alternative: `gemma4:e4b`, already installed) → **`gemma4:e4b` for all languages**

---

## Log

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
  - Spanish grammatical gender: the model mostly falls back to the generic masculine ("obligado", "estancado", "quieto"); the regex check catches only common cases and costs retries. Open product question: neutral wording vs. a per-user grammatical-gender setting.
  - Favorite images repeat across days ("flotter Spaziergang" 6×, "maullido" 5×).
  - Occasional small German slips ("auch wenn es dir kostet", "Samstag's") and a nickname despite the rule ("kleine Maus").
  - Spanish occasionally slips into plural address ("os", "comáis") when talking about the reader and someone else.
- **Fix after v4:** English headlines lowercased weekdays ("for saturday") → sentence-case rule now keeps proper nouns capitalized.

## Open from M1

- On quiet days (e.g. Sam, 2026-10-03) the selection consists only of house placements → check whether the LLM makes good readings from that.
- A Moon placement can be selected next to a Moon aspect, which partly repeats the Moon.

## M1 tuning log (done)

- **2026-10-03, first run:** paws too extreme (1 and 5 on ~40% of days) and a constant positive bias in love. Cause: placements were mapped to categories by planet, so "Venus in any house" pushed love up every day for everyone. Fix: placements count only through their house; the background theme counts half (`background_score_share: 0.5`).
- **2026-10-03, calibration:** over 40 random charts × 20 days the raw scores had a small positive bias (+0.1, more harmonious than tense aspect types). `score_scale: 1.0`, `score_center: 0.1` → paws 1–5 ≈ 7 / 25 / 33 / 26 / 7 %. Days without any Moon aspect: ~4% (Moon placement used instead).
- **Demo profiles, 2026-10-01 + 30 days:** all five poses occur; Lucía is above average this month (her chart, not a bias).

## Deferred to later milestones

- City search (GeoNames `cities1000`, `timezonefinder`) → M3, with onboarding.
- "Why Mira says this" texts in EN/ES/DE → M4 (the review report uses English descriptions).
- Storing readings and recent-reading lookup from the database → M3 (M2 keeps recent readings in memory during a review run).
