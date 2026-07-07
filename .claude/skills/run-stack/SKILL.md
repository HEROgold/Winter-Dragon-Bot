---
name: run-stack
description: Start and smoke-check the WinterDragonV2 docker compose stack (postgres, redis, pgadmin, grafana, redis-commander). Use when asked to run the stack, start docker services, bring up the database/redis, or check service health.
---

# Run: docker compose stack

All commands from the repo root. Docker Desktop must be running (verified against server 29.5.2).

**Do not `docker compose up` the whole file.** The `bot`, `api`, and `workers` services run `python -m winter_dragon[.api|.workers]`, but `src/winter_dragon/` is an empty package mid-rewrite — those containers crash-loop. The infra services are what works.

## Run (agent path) — verified 2026-07-07

```powershell
docker compose up -d postgres redis redis-commander pgadmin grafana
```

Postgres and redis have healthchecks; compose waits for `Healthy` before starting the UIs. Then smoke-check everything:

```powershell
docker compose exec -T postgres pg_isready -U postgres -d winter_dragon   # -> accepting connections
docker compose exec -T redis redis-cli ping                               # -> PONG
curl -s -o /dev/null -w "%{http_code}" http://localhost:5050/   # pgAdmin  -> 302 (login redirect)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3002/   # Grafana  -> 302 (login redirect)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/   # Redis Commander -> 200
```

Default credentials (compose fallbacks): pgAdmin `admin@example.com`/`admin123`, Grafana `admin`/`admin123`, DB `postgres`/`postgres` on database `winter_dragon` (postgres is `expose`d to the compose network only, not published to the host).

## Build (the image is fine; the entry point isn't)

```powershell
docker compose build bot
```

Verified to complete (exit 0, 2026-07-07) — the multi-stage Dockerfile builds `python:3.15-rc-slim-trixie` + `uv sync --frozen --no-dev` cleanly. The image is healthy; it's only the runtime `CMD ["python", "-m", "winter_dragon"]` that fails because the module has no `__main__`. So "the build is broken" and "the container won't run" are different problems — the build is not the issue.

## Stop

```powershell
docker compose down          # keep volumes (postgres/grafana data persist)
```

## Gotchas

- `bot`/`api`/`workers` services: the Dockerfile CMD is `python -m winter_dragon` and compose overrides use `winter_dragon.api` / `winter_dragon.workers` — none of those modules exist yet. Until the rewrite lands an entry point, run app code on the host (see run-wd-discord skill) against this dockerized infra.
- The compose file publishes no postgres port; to reach it from the host tooling use `docker compose exec postgres psql -U postgres winter_dragon`.
