# AstroCat API

Astrology engine, Mira's readings via Ollama, and the FastAPI service with database, login and scheduler. See [../concept.md](../concept.md) and [../TASKS.md](../TASKS.md).

For running the whole service, see the [root README](../README.md). For development on the Mac:

```sh
uv sync
docker compose -f ../compose.yaml -f ../compose.dev.yaml up -d db   # PostgreSQL on 127.0.0.1:55432
uv run astrocat migrate
uv run astrocat serve                                               # API on :8000, with the scheduler
uv run pytest                                                       # database tests use a separate astrocat_test database
uv run astrocat chart --profile demo/anna.yaml
uv run astrocat day --profile demo/anna.yaml --date 2026-10-03            # full engine output
uv run astrocat day --profile demo/anna.yaml --date 2026-10-03 --payload  # LLM payload
uv run astrocat review --profile demo/anna.yaml --profile demo/sam.yaml --from 2026-10-01 --days 30 --engine-only

# Readings via Ollama (gemma4:e4b by default)
uv run astrocat reading --profile demo/anna.yaml --date 2026-10-03 [--lang en]
uv run astrocat review --profile demo/lucia.yaml --from 2026-10-01 --days 14 [--lang de] [--model gemma4:e2b]
uv run pytest
uv run ruff check . && uv run ruff format .
```

Tuning lives in `src/astrocat/engine/data/settings.yaml` (orbs, weights, scoring) and `keywords.yaml` (interpretation keywords). Changing either changes the engine version, so cached readings are regenerated.

Mira's prompt, the language packs (localized names, style example, cliché list, checks, fallback texts) live in `src/astrocat/llm/data/`. Changing them changes the prompt version stored with every reading.

Environment: `OLLAMA_BASE_URL` (default `http://localhost:11434`), `OLLAMA_MODEL` (default `gemma4:e4b`), `OLLAMA_TIMEOUT` (seconds, default 120).

Demo profiles in `demo/` are fictional.
