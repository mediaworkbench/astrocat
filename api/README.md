# AstroCat API

Astrology engine (M1) — later also the FastAPI service. See [../concept.md](../concept.md) and [../TASKS.md](../TASKS.md).

```sh
uv sync
uv run astrocat chart --profile demo/anna.yaml
uv run astrocat day --profile demo/anna.yaml --date 2026-10-03            # full engine output
uv run astrocat day --profile demo/anna.yaml --date 2026-10-03 --payload  # LLM payload
uv run astrocat review --profile demo/anna.yaml --profile demo/sam.yaml --from 2026-10-01 --days 30 --engine-only
uv run pytest
uv run ruff check . && uv run ruff format .
```

Tuning lives in `src/astrocat/engine/data/settings.yaml` (orbs, weights, scoring) and `keywords.yaml` (interpretation keywords). Changing either changes the engine version, so cached readings are regenerated.

Demo profiles in `demo/` are fictional.
