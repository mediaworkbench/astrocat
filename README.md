# AstroCat

Daily horoscopes, delivered by a cat. Mira writes each user's personal reading from their birth chart and today's planets, in English, Spanish or German. A deterministic astrology engine decides what the day looks like; a local LLM (Ollama) only decides how to say it.

Concept: [concept.md](concept.md) · progress and logs: [TASKS.md](TASKS.md) · API and engine: [api/README.md](api/README.md)

## Requirements

- Docker (Docker Desktop on macOS)
- [Ollama](https://ollama.com) running on the host, with the model pulled: `ollama pull gemma4:e4b`

## Setup

```sh
cp .env.example .env                 # then set POSTGRES_PASSWORD to a long random value
docker compose up -d --build         # db + api; migrations run automatically
docker compose exec api astrocat places import       # city list for birth places (one-time, ~10 MB download)
docker compose exec api astrocat create-user anna --display-name Anna --language de
```

Users then log in and complete onboarding in the app (frontend: milestone M4). Until then, the API is reachable for development with `docker compose -f compose.yaml -f compose.dev.yaml up -d` at <http://localhost:8000/api/docs>.

Other admin commands: `astrocat reset-password <username>`, `astrocat migrate`.

## Data and license

- Birth data stays on your machine; there is no telemetry and no external API at runtime.
- City data: [GeoNames](https://www.geonames.org/) (CC BY 4.0).
- License: AGPL-3.0 (required by `libephemeris`).
