# Planned: web dashboard, HTTP API and workers

!!! warning "Not built yet"
    Nothing on this page exists in the `v2` code. It describes the intended design, so that the pieces
    already in place (the `api`/`workers` services in `docker-compose.yml`, `wd_db.extras.api`) make sense.
    Implemented APIs are in the [API reference](reference/index.md).

## HTTP API

A FastAPI service (`python -m winter_dragon.api`, port 8001) with interactive docs at `/docs` and `/redoc`.

- **Auth:** Discord OAuth2. `GET /api/auth/discord/login` redirects to Discord, and
  `POST /api/auth/discord/callback` exchanges the code for a bearer token. Every other endpoint requires
  `Authorization: Bearer <token>`.
- **User data:** `GET /api/user/{discord_id}` (profile), `DELETE /api/user/{discord_id}/data` (GDPR deletion
  request, `202 Accepted`), `GET /api/user/{discord_id}/audit` (deletion audit trail, paginated with
  `limit`/`offset`).
- **Conventions:** FastAPI's `{"detail": ...}` error bodies, `limit` (max 100) / `offset` pagination, and
  per-token rate limiting reported in `X-RateLimit-*` headers.

## Web dashboard

A React + Bun single-page app on port 3000. Users log in with Discord, see their profile and the data the bot
stores about them, and can request its deletion. It talks only to the HTTP API above.

## Background workers

A Redis-backed job queue (`python -m winter_dragon.workers`) for work that shouldn't run on the gateway
event loop: scheduled jobs, heavy computation, and processing deletion requests.

## What exists toward this

- `docker-compose.yml` defines the `api` and `workers` services and Redis.
- `wd_db.extras.api` holds an `APIModel` base for exposing SQLModel tables through the API.
- The `main` branch's version of these features is listed under
  [Platform & Services](features/platform.md).
