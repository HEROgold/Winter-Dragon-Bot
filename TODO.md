# TODO — Docker Compose stack issues

Generated from `docker compose logs` across every service in [docker-compose.yml](docker-compose.yml).

## Status summary

| Service | Image / build | State | Working? |
|---|---|---|---|
| redis | `redis:8.2.4-alpine3.22` | Up (healthy) | ✅ |
| redis-commander | `ghcr.io/joeferner/redis-commander` | Up (healthy) | ✅ |
| postgres | `postgres:14-alpine` | Up (healthy) | ✅ |
| pgadmin | `dpage/pgadmin4` | Up | ✅ (warnings only) |
| grafana | `grafana/grafana-oss` | Up | ✅ |
| **bot** | built from [Dockerfile](Dockerfile) | **Restarting (crash loop)** | ❌ |
| **workers** | built from [Dockerfile](Dockerfile) | **Restarting (crash loop)** | ❌ |
| **api** | built from [Dockerfile](Dockerfile) | **Restarting (crash loop)** | ❌ |

## Broken — application containers (must fix)

### 1. `bot` — no runnable entrypoint
Log repeats endlessly:
```
No module named winter_dragon.__main__; 'winter_dragon' is a package and cannot be directly executed
```
- [Dockerfile](Dockerfile#L71) runs `CMD ["python", "-m", "winter_dragon"]`, but [src/winter_dragon/__init__.py](src/winter_dragon/__init__.py) is an **empty** package with no `__main__.py`.
- The actual bot code lives in the `wd_bot` namespace package ([wd-bot/src/wd_bot/bot.py](wd-bot/src/wd_bot/bot.py)), not under `winter_dragon`.
- There is currently **no top-level entrypoint anywhere** — a grep for `def main` / `__main__` / `asyncio.run` / `.run(` across `wd-bot` and `wd-core` returns nothing. The bot is never actually started.
- **TODO:** create a real entrypoint (`src/winter_dragon/__main__.py`, or a `[project.scripts]` console script) that constructs and runs the `WinterDragon` bot from `wd_bot`.

### 2. `workers` — module does not exist
Log repeats endlessly:
```
No module named winter_dragon.workers
```
- [docker-compose.yml](docker-compose.yml#L84) runs `python -m winter_dragon.workers`, but no `winter_dragon/workers` module exists.
- **TODO:** implement `winter_dragon.workers` (background/task worker), or point the compose command at wherever worker logic should live (e.g. [wd-bot/src/wd_bot/tasks.py](wd-bot/src/wd_bot/tasks.py) / [routines.py](wd-bot/src/wd_bot/routines.py)).

### 3. `api` — module does not exist
Log repeats endlessly:
```
No module named winter_dragon.api
```
- [docker-compose.yml](docker-compose.yml#L151) runs `python -m winter_dragon.api`, but no `winter_dragon.api` module exists.
- Some API model code exists under [wd-db/src/wd_db/extras/api/](wd-db/src/wd_db/extras/api/), but there is no runnable API service (no ASGI app / server entrypoint) exposed on the configured port `8001`.
- **TODO:** implement the `winter_dragon.api` service (web server bound to `0.0.0.0:8001`), or repoint the command.

### Root cause (shared)
The `winter_dragon` distribution package is a stub. The Dockerfile, `bot`, `workers`, and `api` commands all assume a `winter_dragon` package tree (`__main__`, `.workers`, `.api`) that has not been written yet. Until entrypoints exist, all three build-based services will crash-loop and **no DB schema/migrations are ever applied** (the `winter_dragon` database is created empty).

## Configuration gaps

- [ ] `.env` still has a placeholder `DISCORD_CLIENT_ID=your-client-id` (surfaced by `docker compose config`). Set a real Discord client ID for the `api` service ([docker-compose.yml](docker-compose.yml#L155)).
- [ ] Confirm a Discord bot token is provided to the `bot` service. The compose file passes `REDIS_HOST`/`DATABASE_URL` but no token env var — verify [config.ini](config.ini) / `.env` carries it, otherwise the bot cannot authenticate once it starts.
- [ ] No database migration step runs anywhere in the stack. Decide where schema creation/migrations execute (entrypoint, init container, or the `bot`/`api` startup).

## Non-blocking warnings (informational, no action needed)

- **postgres:** `sh: locale: not found` / "no usable system locales" — cosmetic, expected on Alpine.
- **redis:** `Could not create command: _FT.DROP` etc. — internal RediSearch module registration notices, not errors. Redis reports `Ready to accept connections`.
- **pgadmin:** `SyntaxWarning: 'return' in a 'finally' block` from bundled `sshtunnel.py` — upstream dependency warning; pgAdmin boots and listens on `:80` (mapped to `5050`).
- **grafana:** only routine `cleanup` / `plugins.update.checker` / bleve index logs — healthy.
