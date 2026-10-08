---
name: run-stack
description: Start and smoke-check the WinterDragonV2 docker compose stack (postgres, redis, pgadmin, grafana, redis-commander). Use when asked to run the stack, start docker services, bring up the database/redis, or check service health.
---

# Run: docker compose stack

All commands from the repo root. Docker Desktop must be running (verified against server 29.5.2).

**Do not `docker compose up` the whole file.** `api` and `workers` run `python -m winter_dragon.api` / `.workers`, which don't exist — they crash-loop. `bot` runs `python -m winter_dragon`, which now exists (`src/winter_dragon/__main__.py`), but the container has not been re-verified since. Bring up the infra services, and run the bot on the host (run-wd-discord skill) unless you are deliberately testing the container.

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

## Build

```powershell
docker compose build bot
```

Verified to complete (exit 0, 2026-07-07) — the multi-stage Dockerfile builds `python:3.15-rc-slim-trixie` + `uv sync --frozen --no-dev` cleanly. The build and the container runtime are separate problems: a green build says nothing about whether `CMD ["python", "-m", "winter_dragon"]` reaches READY (it needs the token in the mounted `config.ini` and a reachable postgres).

## Stop

```powershell
docker compose down          # keep volumes (postgres/grafana data persist)
```

## Gotchas

- `api`/`workers` services: `winter_dragon.api` / `winter_dragon.workers` don't exist; there is no HTTP API or worker service in the tree yet (see docs/planned.md).
- The compose file publishes no postgres port; to reach it from the host tooling use `docker compose exec postgres psql -U postgres winter_dragon`.
