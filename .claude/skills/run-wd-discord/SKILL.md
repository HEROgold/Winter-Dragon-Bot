---
name: run-wd-discord
description: Run and drive the Winter Dragon Discord bot / wd-discord client live against Discord — REST auth check and real gateway connection. Use when asked to run the bot, start the Discord client, verify a wd-discord change against the live API, or smoke-test gateway/REST behavior.
---

# Run: the Discord client (live)

All paths relative to the repo root. **There is currently no bot entry point** — `src/winter_dragon/` is an empty package (the Dockerfile's `python -m winter_dragon` would crash), because the project is mid-rewrite replacing discord.py with the in-house `wd_discord` client. The runnable app surface is `wd_discord` itself, driven live by the committed driver.

## Prerequisites

- `uv` on PATH (0.11.x works); deps installed via `uv sync` (a plain `uv run` also resolves them).
- A real bot token in `config.ini` under `[Tokens] discord_token`. The value `!!` is the "unset" sentinel — the driver refuses it with exit code 2. Never print this file's contents.

## Run (agent path)

```powershell
uv run python .claude/skills/run-wd-discord/driver.py
```

Verified output shape (ran 2026-07-07, exit 0):

```text
REST OK: authenticated as TBot (id 12268...)
REST OK: gateway url wss://gateway.discord.gg, recommended shards 1
GATEWAY OK: READY session 3bb18e2b..., user TBot
GATEWAY OK: closed cleanly
```

The driver exercises: `Client.get_current_user()` and `get_gateway_bot()` (REST, errors-as-values — a failure comes back as `ApiResponseError`, not an exception), then `Gateway.connect()` through HELLO → IDENTIFY → READY, then `Gateway.close()`. Extend the driver (send `update_presence`, fetch a guild) rather than writing throwaway scripts.

## Direct invocation

Most wd-discord PRs touch one function. Import and call it directly:

```powershell
uv run python -c "from wd_discord.gateway import parse_ready; print(parse_ready({'d': {'session_id': 's', 'resume_gateway_url': 'u'}}))"
```

`build_presence`, `parse_ready`, `build_identify` in `wd_discord/gateway/connection.py` are pure functions designed for exactly this.

## Gotchas

- The gateway `connect()` blocks until READY; wrap in `asyncio.wait_for(..., timeout=30)` like the driver does, or a bad token hangs the run.
- `Client` responses: check `isinstance(result, Response)` (from `httpxyz`) before `.json()` — the union return means pyright rejects blind attribute access.
- Docker's bot service and `docker compose up bot` do **not** work right now (no `winter_dragon.__main__`); see the run-stack skill for what does.
