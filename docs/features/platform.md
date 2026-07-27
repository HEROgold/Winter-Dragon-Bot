# Platform & Services

Everything around the Discord process: the REST API and web dashboard, the distributed task queue, the data layer, observability, and how it is all deployed.

Audience: operators and anyone building against the bot.

!!! danger "Largest parity gap"
    Almost nothing on this page has a `v2` counterpart yet. The API, the frontend, the queue, the workers, and the database table models are all absent from the workspace.

---

## REST API

A FastAPI service that runs alongside the bot and backs the web dashboard:

- **Discord OAuth** — a login redirect and a callback that exchanges the code and issues a bearer token.
- **User profile** — a summary of the data the bot holds about a Discord user, behind bearer-token verification.
- **Data deletion** — a GDPR-style soft delete of a user's data, recorded with an audit trail.
- **Deletion audit** — read back the deletion history for a user.

**Status:** ❌ Missing — no API package on `v2`; the `api` service in `docker-compose.yml` points at a module that does not exist.
**Source on `main`:** `src/winter_dragon/bot/api/`

## Web dashboard

A React frontend served by Bun, offering Discord OAuth sign-in and an authenticated view of the user's own data, including the deletion flow above.

**Status:** ❌ Missing — `wd-frontend/` exists on `v2` but is empty.
**Source on `main`:** `frontend/`

## Task queue and workers

Long-running or bursty work is pushed out of the bot process onto a Redis-backed RQ queue, so the gateway connection is never blocked by scraping or batch jobs.

- **Queue management** — enqueue tasks with priority, look up jobs, read queue length and statistics, clear a queue.
- **Queue monitoring** — periodic statistics over the queues.
- **Worker runner** — a standalone entrypoint that consumes queues, optionally several processes at once and optionally restricted to named queues.
- **Autoscaler** — a supervisor that watches queue depth and starts or stops worker processes to match the current load.
- **Tasks** — Steam sale scraping is the queue's main workload on `main`, running independently of the bot.

**Status:** ❌ Missing — no `redis` or `workers` package on `v2`.
**Source on `main`:** `src/winter_dragon/redis/`, `src/winter_dragon/workers/`

## Data layer

PostgreSQL through SQLModel, with roughly sixty table models covering users, guilds, roles, channels, messages, presence, and command usage, plus per-feature tables — audit logs, autochannels, infractions, lobbies, reminders, Steam sales and subscribers, hangman, the incremental game economy, synced bans, LoL accounts, matchmaking and team compositions, and data-deletion records.

Shared model machinery sits above them: a common base model, API-exposed table variants, and a startup check that verifies the expected tables exist.

**Status:** ❌ Missing for the models — `wd-db` on `v2` has the extension/model machinery, constants, and keys, but **no `tables/` package**. This is the single biggest blocker for the cog ports.
**Source on `main`:** `src/winter_dragon/database/`

## Shared UI toolkit

A reusable layer over Discord's component API — buttons, selects, modals, menus, views, and a paginator with a page-jump modal. Features build interactive flows out of these rather than reimplementing component plumbing, which is why so many cogs depend on it.

**Status:** ❌ Missing — no `wd-*` home on `v2`, yet the log aggregator, hangman, command manager, sync, welcome, and Steam sales menu all import it.
**Source on `main`:** `src/winter_dragon/bot/ui/`

## Observability

- **Prometheus** — exposes bot metrics on a scrape endpoint (enabled in debug environments on `main`).
- **Bot performance** — in-Discord resource and latency reporting, including a rendered graph.
- **Grafana** — dashboards over logs and the Postgres database.
- **pgAdmin / redis-commander** — administrative UIs for the datastores.
- **Sentry** — error reporting (see [Bot Core](bot-core.md)).

**Status:** 🟡 for the Prometheus and metrics cogs (copied into `wd-cogs`, unwired). ✅ for Sentry. Grafana, pgAdmin, and redis-commander are compose services and are present on `v2`.
**Source on `main`:** `src/winter_dragon/bot/extensions/bot_extension/prometheus.py`, `bot_metrics.py`, `docker-compose.yml`

## Deployment

A Docker Compose stack runs the whole system: Redis, Postgres, the bot, the workers, the API, the frontend, and the administrative UIs (pgAdmin, Grafana, redis-commander).

**Status:** 🟡 The compose file exists on `v2`, but the `bot`, `workers`, and `api` services all crash-loop because their entrypoint modules do not exist — see [TODO.md](https://github.com/HEROgold/Winter-Dragon-Bot/blob/v2/TODO.md).
**Source on `main`:** `docker-compose.yml`, `bot-dockerfile`
