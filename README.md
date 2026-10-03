# AstroCat

Daily horoscopes, delivered by a cat. Mira writes each user's personal reading from their birth chart and today's planets, in English, Spanish or German. A deterministic astrology engine decides what the day looks like; a local LLM (Ollama) only decides how to say it.

Concept: [concept.md](concept.md) · progress and logs: [TASKS.md](TASKS.md) · API and engine: [api/README.md](api/README.md)

## Requirements

- Docker (Docker Desktop on macOS)
- [Ollama](https://ollama.com) running on the host, with the model pulled: `ollama pull gemma4:e4b`

## Setup

```sh
cp .env.example .env                 # then set POSTGRES_PASSWORD to a long random value
docker compose up -d --build         # web (port 80) + api + db; migrations run automatically
docker compose exec api astrocat places import       # city list for birth places (one-time, ~10 MB download)
docker compose exec api astrocat create-user anna --display-name Anna --language de
```

Then open `http://<ip-of-the-mac>/` on a phone in the same Wi-Fi, log in, and complete onboarding. In Safari, "Add to Home Screen" turns it into an app icon.

- Give the Mac a fixed IP (DHCP reservation in the router) and allow incoming connections for Docker in the macOS firewall.
- The Mac must be awake for the app to be reachable; readings missed while it slept are generated on the next visit or scheduler run.
- Development: `docker compose -f compose.yaml -f compose.dev.yaml up -d` additionally publishes the API on <http://localhost:8000/api/docs> and the database on 127.0.0.1:55432; `cd web && npm run dev` runs the app with hot reload on port 5173.

Other admin commands: `astrocat reset-password <username>`, `astrocat migrate`.

## Data and license

- Birth data stays on your machine; there is no telemetry and no external API at runtime.
- City data: [GeoNames](https://www.geonames.org/) (CC BY 4.0).
- License: AGPL-3.0 (required by `libephemeris`).
